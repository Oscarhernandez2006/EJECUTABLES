"""Consultas parametrizadas de Siesa y captura confiable de transformaciones."""

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree as ET

import openpyxl
import requests
from openpyxl.styles import Font, PatternFill

from config.empresas import empresa_valida
from . import siesa
from .inventario_documentos import DocumentosInventario, texto, numero
from .taller_calculos import calcular, decimal_positivo


RECURSOS = {"centros", "bodegas", "listas", "productos", "lotes", "detalle"}
SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
SERVICIO = "http://tempuri.org/"
RUTAS_REST = {"centros": "centros-operacion", "bodegas": "bodegas", "listas": "listas-precios",
              "productos": "productos", "lotes": "lotes", "detalle": "detalle-item"}


class ConsultaNoDisponible(RuntimeError):
    pass


def contexto(valores):
    empresa = str(valores.get("empresa", ""))
    if not empresa_valida(empresa):
        raise ValueError("Selecciona una empresa válida.")
    fecha = str(valores.get("fecha", ""))
    try:
        if len(fecha) != 8 or not fecha.isdigit():
            raise ValueError
        datetime.strptime(fecha, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("Indica una fecha válida en formato AAAAMMDD.") from exc
    return {"empresa": empresa, "fecha": fecha, **{
        clave: texto(valores.get(clave, ""), clave, ancho, obligatorio=False)
        for clave, ancho in (("co", 3), ("bodega", 5), ("lista", 20),
                             ("q", 100), ("item", 50), ("lote", 15))
    }}


def clave_api():
    return os.getenv("SIESA_CONSULTAS_API_KEY") or os.getenv("API_KEY", "")


def fecha_hoy():
    return datetime.now(timezone(timedelta(hours=-5))).strftime("%Y%m%d")


def proveedor_consultas():
    if clave_api() or not any(os.getenv("SIESA_TALLER_XML_" + recurso.upper()) for recurso in RECURSOS):
        return "rest"
    return "soap"


def configuracion(empresa_id=None):
    if proveedor_consultas() == "rest":
        return [] if clave_api() else ["SIESA_CONSULTAS_API_KEY o API_KEY"]
    return [recurso for recurso in sorted(RECURSOS)
            if not os.getenv("SIESA_TALLER_XML_" + recurso.upper())]


def nombre_local(tag):
    return tag.rsplit("}", 1)[-1]


def conexion_rest():
    base = (os.getenv("SIESA_CONSULTAS_BASE_URL") or os.getenv("SIESA_CONSULTAS_URL")
            or "https://apiconsulta.grupo-santacruz.com").strip().rstrip("/")
    partes = urlsplit(base)
    if partes.scheme != "https" or not partes.hostname or partes.username or partes.password or partes.query or partes.fragment:
        raise ConsultaNoDisponible("La API de consultas debe usar una URL HTTPS válida, sin credenciales ni parámetros.")
    ruta = partes.path.rstrip("/")
    if not ruta.endswith("/carnes-frias"):
        ruta += "/carnes-frias"
    try:
        timeout_ms = int(os.getenv("SIESA_CONSULTAS_TIMEOUT_MS", "30000"))
        if not 1 <= timeout_ms <= 300000:
            raise ValueError
    except ValueError as exc:
        raise ConsultaNoDisponible("SIESA_CONSULTAS_TIMEOUT_MS debe ser un entero entre 1 y 300000.") from exc
    segundos = timeout_ms / 1000
    return urlunsplit((partes.scheme, partes.netloc, ruta, "", "")), (min(5, segundos), segundos)


def consultar(recurso, filtros):
    if recurso not in RECURSOS:
        raise ValueError("Consulta no permitida.")
    filtros_originales = filtros
    filtros = contexto(filtros)
    if proveedor_consultas() == "rest":
        return consultar_rest(recurso, filtros, filtros_originales=filtros_originales)
    plantilla = os.getenv("SIESA_TALLER_XML_" + recurso.upper())
    if not plantilla:
        raise ConsultaNoDisponible(
            f"Falta configurar la consulta Siesa de {recurso}. Contacta al administrador.")
    valores = {**filtros, "usuario": siesa.SIESA_USER, "clave": siesa.SIESA_PASSWORD,
               "conexion": siesa.NOMBRE_CONEXION}
    try:
        parametros = ET.fromstring(plantilla)
        for nodo in parametros.iter():
            if nodo.text and nodo.text.startswith("{") and nodo.text.endswith("}"):
                nodo.text = valores[nodo.text[1:-1]]
    except (ET.ParseError, KeyError) as exc:
        raise ConsultaNoDisponible("La plantilla XML de consulta Siesa no es válida.") from exc
    sobre = ET.Element(f"{{{SOAP}}}Envelope")
    cuerpo = ET.SubElement(sobre, f"{{{SOAP}}}Body")
    metodo = ET.SubElement(cuerpo, f"{{{SERVICIO}}}EjecutarConsultaXML")
    ET.SubElement(metodo, f"{{{SERVICIO}}}pvstrxmlParametros").text = ET.tostring(
        parametros, encoding="unicode")
    try:
        respuesta = requests.post(
            siesa.URL_SERVICIO, data=ET.tostring(sobre, encoding="utf-8", xml_declaration=True),
            headers={"Content-Type": "text/xml; charset=utf-8",
                     "SOAPAction": '"http://tempuri.org/EjecutarConsultaXML"'}, timeout=(5, 25),
        )
        respuesta.raise_for_status()
        raiz = ET.fromstring(respuesta.content)
    except (requests.RequestException, ET.ParseError) as exc:
        raise ConsultaNoDisponible("No se pudo consultar Siesa. Intenta actualizar nuevamente.") from exc
    if any(nombre_local(nodo.tag) in {"Fault", "f_detalle"} for nodo in raiz.iter()):
        raise ConsultaNoDisponible("Siesa rechazó la consulta. Revisa permisos y configuración.")
    filas = []
    for nodo in raiz.iter():
        hijos = list(nodo)
        if not hijos or any(list(hijo) for hijo in hijos):
            continue
        fila = {nombre_local(hijo.tag).lower(): (hijo.text or "").strip() for hijo in hijos}
        if "codigo" in fila:
            filas.append(fila)
    if recurso == "detalle":
        coincidencias = [fila for fila in filas if fila["codigo"] == filtros["item"]]
        if len(coincidencias) != 1:
            raise ConsultaNoDisponible("Siesa no devolvió un detalle único para el ítem, bodega y lote.")
        return normalizar_detalle(coincidencias[0])
    requeridos = {"codigo", "descripcion"}
    if recurso == "productos":
        requeridos |= {"referencia", "um"}
    if any(not requeridos.issubset(fila) for fila in filas):
        raise ConsultaNoDisponible("La consulta Siesa no devuelve las columnas requeridas.")
    return filas[:40] if recurso == "productos" else filas


def consultar_rest(recurso, filtros, filtros_originales=None):
    clave = clave_api()
    if not clave:
        raise ConsultaNoDisponible("Falta configurar la clave de la API de consultas en el servidor.")
    if recurso == "detalle" and filtros["fecha"] != fecha_hoy():
        raise ValueError("La API de consultas solo permite existencia y costo al corte de hoy (Colombia).")
    base, timeout = conexion_rest()
    parametros = dict(filtros)
    if recurso == "lotes":
        parametros["solo_con_existencia"] = "true" if (filtros_originales or {}).get("solo_con_existencia", "true") in (True, "true") else "false"
    try:
        respuesta = requests.get(
            f"{base}/{RUTAS_REST[recurso]}", params=parametros,
            headers={"X-API-Key": clave, "Accept": "application/json", "Cache-Control": "no-cache"},
            timeout=timeout, allow_redirects=False,
        )
        if respuesta.status_code in {401, 403}:
            raise ConsultaNoDisponible("La API rechazó la clave de acceso. Revisa la configuración del servidor.")
        if respuesta.status_code in {400, 404, 422}:
            datos_error = respuesta.json()
            detalle = datos_error.get("detail") if isinstance(datos_error, dict) else None
            if isinstance(detalle, str) and "solo disponible para la empresa 8" in detalle.lower():
                raise ConsultaNoDisponible(
                    f"La API de consultas todavía restringe el acceso a la compañía 8 y rechazó la compañía {filtros['empresa']}. "
                    "Es necesario habilitar esta compañía en el servidor de la API; las variables de entorno no eliminan esa restricción.")
            raise ValueError(detalle if isinstance(detalle, str) else "Revisa los parámetros de la consulta de Siesa.")
        if respuesta.status_code != 200:
            raise ConsultaNoDisponible("La API de consultas no está disponible. Intenta actualizar nuevamente.")
        datos = respuesta.json()
    except (requests.RequestException, requests.exceptions.JSONDecodeError) as exc:
        raise ConsultaNoDisponible("No se pudo consultar la API de Siesa. Intenta actualizar nuevamente.") from exc
    if not isinstance(datos, dict):
        raise ConsultaNoDisponible("La API devolvió una respuesta de consulta no válida.")
    if "empresa" in datos and str(datos["empresa"]) != filtros["empresa"]:
        raise ConsultaNoDisponible("La API devolvió datos de otra compañía. Se bloqueó la respuesta para evitar mezclar inventarios.")
    if recurso == "detalle":
        if datos.get("codigo") != filtros["item"] or datos.get("fecha_corte") != filtros["fecha"]:
            raise ConsultaNoDisponible("El ítem o la fecha de corte no coinciden con la consulta.")
        if any(not isinstance(datos.get(campo), bool) for campo in ("tiene_costo", "tiene_precio", "incluye_impuestos")):
            raise ConsultaNoDisponible("Faltan los indicadores de costo, precio o impuestos en la API.")
        if datos["tiene_precio"] and str(datos.get("um_precio", "")).strip().lower() != str(datos.get("um", "")).strip().lower():
            raise ConsultaNoDisponible("La unidad del precio no coincide con la unidad de inventario.")
        return normalizar_detalle(datos)
    filas = datos.get("data")
    requeridos = {"codigo", "descripcion"} | ({"referencia", "um"} if recurso == "productos" else set())
    if not isinstance(filas, list) or any(
            not isinstance(fila, dict) or not requeridos.issubset(fila)
            or any(not isinstance(fila[campo], str) for campo in requeridos) for fila in filas):
        raise ConsultaNoDisponible("La API no devolvió el catálogo esperado.")
    if recurso == "lotes":
        if not isinstance(datos.get("maneja_lote"), bool) or (not datos["maneja_lote"] and filas):
            raise ConsultaNoDisponible("La API no indicó correctamente si el ítem maneja lotes.")
        return {"maneja_lote": datos["maneja_lote"], "data": filas}
    return filas[:40] if recurso == "productos" else filas


def normalizar_detalle(fila):
    requeridos = {"codigo", "descripcion", "referencia", "um", "existencia",
                  "costo_promedio", "precio_venta"}
    if not requeridos.issubset(fila) or any(not fila[c] for c in ("codigo", "referencia", "um")):
        raise ConsultaNoDisponible("Faltan datos de inventario, costo o precio en la respuesta de Siesa.")
    resultado = {clave: fila[clave] for clave in requeridos}
    for campo in ("tiene_costo", "tiene_precio", "incluye_impuestos", "fecha_corte",
                  "valoracion_costo", "um_precio", "avisos"):
        if campo in fila:
            resultado[campo] = fila[campo]
    try:
        existencia = Decimal(str(fila["existencia"]))
        if not existencia.is_finite():
            raise ValueError
        resultado["existencia"] = float(existencia)
        for campo in ("costo_promedio", "precio_venta"):
            resultado[campo] = float(decimal_positivo(fila[campo], campo, permitir_cero=True))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ConsultaNoDisponible("Siesa devolvió existencias, costo o precio no válidos.") from exc
    return resultado


def preparar_captura(payload):
    if not isinstance(payload, dict):
        raise ValueError("El taller debe ser un objeto JSON.")
    filtros = contexto(payload)
    if proveedor_consultas() == "rest" and filtros["fecha"] != fecha_hoy():
        raise ValueError("La API de consultas exige que la fecha del taller sea hoy (Colombia).")
    talleres = payload.get("talleres")
    if not isinstance(talleres, list) or not 1 <= len(talleres) <= 30:
        raise ValueError("Incluye entre 1 y 30 transformaciones.")
    centros = consultar("centros", filtros)
    if filtros["co"] not in {fila["codigo"] for fila in centros}:
        raise ValueError("El centro de operación no pertenece a la empresa.")
    if filtros["lista"] not in {fila["codigo"] for fila in consultar("listas", filtros)}:
        raise ValueError("Selecciona una lista de precios válida.")
    bodegas = {fila["codigo"] for fila in consultar("bodegas", filtros)}
    consumo = defaultdict(Decimal)
    detalles = {}
    lotes_por_item = {}
    filas = []
    resumenes = []
    numeros = set()
    for taller in talleres:
        if not isinstance(taller, dict):
            raise ValueError("Transformación no válida.")
        consecutivo = numero(taller.get("numero"), "Número", positivo=True, entero=True)
        if consecutivo in numeros:
            raise ValueError("Los números de transformación no se pueden repetir.")
        numeros.add(consecutivo)
        grupos = {}
        for grupo, tipo in (("insumos", "SAI"), ("productos", "EIN")):
            registros = taller.get(grupo)
            if not isinstance(registros, list) or not 1 <= len(registros) <= 100:
                raise ValueError(f"Agrega entre 1 y 100 {grupo}.")
            grupos[grupo] = []
            for registro in registros:
                if not isinstance(registro, dict):
                    raise ValueError("Movimiento no válido.")
                consulta = contexto({**filtros, "bodega": registro.get("bodega", ""),
                                     "item": registro.get("item", ""), "lote": registro.get("lote", "")})
                if consulta["bodega"] not in bodegas or not consulta["item"]:
                    raise ValueError("Selecciona un ítem y una bodega válidos.")
                if proveedor_consultas() == "rest":
                    clave_lotes = (consulta["bodega"], consulta["item"], tipo)
                    if clave_lotes not in lotes_por_item:
                        lotes_por_item[clave_lotes] = consultar("lotes", {
                            **consulta, "solo_con_existencia": "true" if tipo == "SAI" else "false"})
                    lotes = lotes_por_item[clave_lotes]
                    if lotes["maneja_lote"] and consulta["lote"] not in {fila["codigo"] for fila in lotes["data"]}:
                        raise ValueError("Selecciona un lote activo válido. Los lotes nuevos deben crearse primero en Siesa.")
                    if not lotes["maneja_lote"] and consulta["lote"]:
                        raise ValueError("El ítem seleccionado no maneja lote.")
                clave = (consulta["bodega"], consulta["item"], consulta["lote"])
                if clave not in detalles:
                    detalles[clave] = consultar("detalle", consulta)
                detalle = detalles[clave]
                if tipo == "SAI" and detalle.get("tiene_costo") is False:
                    raise ValueError(f"El insumo {detalle['descripcion']} no tiene costo en Siesa. No se puede usar un cero de reemplazo.")
                if tipo == "EIN" and detalle.get("tiene_precio") is False and registro.get("precio_editado") is not True:
                    raise ValueError(f"El producto {detalle['descripcion']} no tiene precio vigente. Ingresa explícitamente el precio de venta.")
                cantidad = decimal_positivo(registro.get("cantidad"), "Cantidad")
                precio = decimal_positivo(registro.get("precio_venta", detalle["precio_venta"]),
                                          "Precio de venta", permitir_cero=True)
                if tipo == "SAI":
                    consumo[clave] += cantidad
                    if consumo[clave] > Decimal(str(detalle["existencia"])):
                        raise ValueError(f"Existencia insuficiente para {detalle['descripcion']} "
                                         f"en bodega {consulta['bodega']} y lote {consulta['lote'] or 'sin lote'}.")
                grupos[grupo].append({**detalle, "cantidad": cantidad, "precio_venta": precio})
                filas.append({"CIA": filtros["empresa"], "CO": filtros["co"], "NUMERO": consecutivo,
                              "TIPO_DOC": tipo, "LOTE": consulta["lote"], "REFERENCIA": detalle["referencia"],
                              "BODEGA": consulta["bodega"], "UM": detalle["um"], "CANT": cantidad,
                              "DESCRIPCION": detalle["descripcion"],
                              "COSTO PROMEDIO SIESA": detalle["costo_promedio"],
                              "PRECIO SIESA": detalle["precio_venta"],
                              "EXISTENCIA SIESA": detalle["existencia"],
                              "INCLUYE IMPUESTOS": detalle.get("incluye_impuestos"),
                              "COSTO UNITARIO": detalle["costo_promedio"] if tipo == "SAI" else None,
                              "PRECIO DE  VENTA": precio})
        resumenes.append({"numero": consecutivo, **calcular(grupos["insumos"], grupos["productos"])})
    parametros = {"UN": texto(payload.get("un", "001"), "UN", 20),
                  "TERCERO": texto(payload.get("tercero", "900326452"), "TERCERO", 15)}
    DocumentosInventario(None, filtros["empresa"], filtros["fecha"], "taller",
                        parametros=parametros, hojas={"Hoja1": filas})
    costo = sum(fila["costo_total"] for fila in resumenes)
    venta = sum(fila["venta_total"] for fila in resumenes)
    return {"Hoja1": filas}, parametros, {"talleres": resumenes, "costo_total": costo,
            "venta_total": venta, "utilidad": venta - costo, "margen": (venta - costo) / venta}


def revision(hojas, parametros, fecha):
    contenido = json.dumps([hojas, parametros, fecha], sort_keys=True, default=str)
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def exportar(hojas, parametros, resumen, filtros):
    proc = DocumentosInventario(None, str(filtros["empresa"]), filtros["fecha"], "taller",
                                parametros=parametros, hojas=hojas)
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Hoja1"
    columnas = ["CIA", "FECHA", "CO", "TIPO_DOC", "NUMERO", "NATURALEZA", "LOTE", "REFERENCIA",
                "DESCRIPCION", "BODEGA", "UM", "CANT", "% PART", "COSTO UNITARIO", "COSTO TOTAL",
                "PRECIO DE  VENTA", "TOTAL VALOR  VENTA", "% RENT"]
    hoja.append(columnas)
    detalle_taller = libro.create_sheet("TALLER")
    detalle_taller.append(["TALLER", "DOCUMENTO", "ITEM", "PRODUCTO", "UM", "CANTIDAD", "PARTICIPACION",
                           "COSTO UNITARIO", "COSTO TOTAL", "PRECIO VENTA", "VENTA TOTAL"])
    consolidado = libro.create_sheet("CONSOLIDADO")
    consolidado.append(["TALLER", "FECHA", "PESO INSUMOS", "PESO PRODUCTOS", "MERMA", "RENDIMIENTO",
                        "COSTO", "VENTA", "UTILIDAD", "MARGEN", "COSTO DE VENTA"])
    catalogo = libro.create_sheet("BD")
    catalogo.append(["REFERENCIA", "DESCRIPCION", "UM", "BODEGA", "LOTE", "EXISTENCIA A LA FECHA",
                     "COSTO PROMEDIO SIESA", "PRECIO SIESA", "PRECIO DE VENTA"])
    resumen_por_numero = {fila["numero"]: fila for fila in resumen["talleres"]}
    for _, fila in proc.datos.iterrows():
        salida = fila["TIPO_DOC"] == "SAI"
        total = resumen_por_numero[fila["NUMERO"]]
        costo = fila["COSTO UNITARIO"] if salida else fila["COSTO_CALCULADO"]
        precio = fila["PRECIO DE  VENTA"]
        participacion = float(fila["CANT"]) / total["peso_insumos"]
        datos = {**fila.to_dict(), "FECHA": filtros["fecha"], "NATURALEZA": "S" if salida else "E",
                 "% PART": participacion, "COSTO UNITARIO": costo, "COSTO TOTAL": costo * fila["CANT"],
                 "TOTAL VALOR  VENTA": precio * fila["CANT"], "% RENT": total["margen"]}
        hoja.append([datos.get(campo) for campo in columnas])
        detalle_taller.append([fila["NUMERO"], fila["TIPO_DOC"], fila["REFERENCIA"], fila["DESCRIPCION"],
                               fila["UM"], fila["CANT"], participacion, costo, costo * fila["CANT"],
                               precio, precio * fila["CANT"]])
        catalogo.append([fila["REFERENCIA"], fila["DESCRIPCION"], fila["UM"], fila["BODEGA"], fila["LOTE"],
                 fila["EXISTENCIA SIESA"], fila["COSTO PROMEDIO SIESA"], fila["PRECIO SIESA"], precio])
    for fila in resumen["talleres"]:
        consolidado.append([fila["numero"], filtros["fecha"], fila["peso_insumos"], fila["peso_productos"],
                            fila["merma"], fila["rendimiento"], fila["costo_total"], fila["venta_total"],
                            fila["utilidad"], fila["margen"], fila["costo_venta"]])
    for pestana in libro:
        pestana.freeze_panes = "A2"
        pestana.auto_filter.ref = pestana.dimensions
        for celda in pestana[1]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="157347")
        for columna in pestana.columns:
            pestana.column_dimensions[columna[0].column_letter].width = min(
                45, max(14, max(len(str(celda.value or "")) for celda in columna) + 2))
            for celda in columna[1:]:
                if isinstance(celda.value, str):
                    celda.data_type = "s"
                elif isinstance(celda.value, (float, Decimal)):
                    celda.number_format = "#,##0.0000"
    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)
    return archivo
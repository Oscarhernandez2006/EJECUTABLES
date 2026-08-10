"""Aplicación web para la carga y ejecución de procesos de integración con Siesa.

Expone una interfaz donde el usuario selecciona el tipo de proceso
(Pedidos, Requisiciones o Sobrecostos), carga el archivo Excel y ejecuta
la importación hacia el servicio web de Siesa.

Diseñado para integrarse posteriormente a un hub de aplicaciones.
"""

import inspect
import json
import os
import tempfile
import traceback

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from procesadores import PROCESADORES
from config import (
    EMPRESAS,
    empresa_valida,
    esquema_de,
    datos_esquema_de,
    admite_parametros_manuales,
)

app = Flask(__name__)

# Carpeta base del proyecto (donde viven las plantillas Excel).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Límite de tamaño de archivo: 25 MB.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

# Extensiones de Excel permitidas.
EXTENSIONES_PERMITIDAS = {".xlsx", ".xlsm", ".xls"}

# Catálogo de procesos, agrupado por categoría para el panel lateral.
# Campos por proceso: id, nombre, descripcion, grupo, hoja, entradas,
# requiere_empresa, requiere_fecha. ``disponible`` se calcula según exista un
# procesador registrado en ``PROCESADORES``.
PROCESOS = [
    # --- Compras -------------------------------------------------------------
    {
        "id": "compra_vacuno", "nombre": "Compra Vacuno", "grupo": "Compras",
        "descripcion": "Factura de compra de ganado vacuno al proveedor.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "compra_porcino", "nombre": "Compra Porcino", "grupo": "Compras",
        "descripcion": "Factura de compra de ganado porcino al proveedor.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    # --- Contable ------------------------------------------------------------
    {
        "id": "cruce_contable", "nombre": "Cruce Contable", "grupo": "Contable",
        "descripcion": "Asiento contable (débito/crédito) de reclasificación de compra.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": False,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    # --- Inventario / Producción --------------------------------------------
    {
        "id": "cargue_lotes", "nombre": "Cargue de Lotes", "grupo": "Inventario",
        "descripcion": "Crea los lotes de producción en Siesa.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "retoma_vacuno", "nombre": "Retoma Vacuno", "grupo": "Inventario",
        "descripcion": "Retoma de despojos / subproductos de vacuno.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "retoma_porcino", "nombre": "Retoma Porcino", "grupo": "Inventario",
        "descripcion": "Retoma de despojos / subproductos de porcino.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "canal_vacuno", "nombre": "Canal Vacuno", "grupo": "Inventario",
        "descripcion": "Entrada de canales de res al inventario.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "canal_porcino", "nombre": "Canal Porcino", "grupo": "Inventario",
        "descripcion": "Entrada de canales de cerdo al inventario.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    # --- Sacrificio / Costos -------------------------------------------------
    {
        "id": "flete_bovino", "nombre": "Flete Bovino", "grupo": "Costos",
        "descripcion": "Factura de fletes de transporte de ganado bovino.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "sacrificio_bovino", "nombre": "Sacrificio Bovino", "grupo": "Costos",
        "descripcion": "Documento de sacrificio / beneficio bovino.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "impuestos_sacrificio", "nombre": "Impuestos Sacrificio", "grupo": "Costos",
        "descripcion": "Impuestos asociados al sacrificio bovino.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [
            {"clave": "analisis", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"},
            {"clave": "impuestos", "etiqueta": "Archivo de impuestos", "archivo": "IMP_SACRIFICIO.xlsx"},
        ],
    },
    # --- Documentos de pedidos ----------------------------------------------
    {
        "id": "doc_pedidos", "nombre": "Doc. Pedidos", "grupo": "Documentos",
        "descripcion": "Genera los documentos de pedidos.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
    {
        "id": "compromisos_pedidos", "nombre": "Compromisos Pedidos", "grupo": "Documentos",
        "descripcion": "Genera los compromisos de los pedidos.", "hoja": "CANAL",
        "requiere_empresa": True, "requiere_fecha": True,
        "entradas": [{"clave": "archivo", "etiqueta": "Archivo de análisis", "archivo": "ANALISIS.xlsx"}],
    },
]


def _marcar_disponibilidad(procesos):
    """Marca cada proceso como disponible y adjunta sus esquemas."""
    for p in procesos:
        p["disponible"] = p["id"] in PROCESADORES
        p["esquema_parametros"] = esquema_de(p["id"])
        p["esquema_datos"] = datos_esquema_de(p["id"])
        p["admite_manual"] = admite_parametros_manuales(p["id"])
    return procesos


PROCESOS = _marcar_disponibilidad(PROCESOS)


def _extension_valida(nombre_archivo):
    _, ext = os.path.splitext(nombre_archivo.lower())
    return ext in EXTENSIONES_PERMITIDAS


def _proceso_por_id(tipo):
    return next((p for p in PROCESOS if p["id"] == tipo), None)


@app.route("/")
def index():
    return render_template(
        "index.html",
        procesos=PROCESOS,
        procesos_json=json.dumps(PROCESOS),
        empresas=EMPRESAS,
        empresas_json=json.dumps(EMPRESAS),
    )


@app.route("/plantilla/<tipo>/<clave>")
def descargar_plantilla(tipo, clave):
    """Descarga el archivo Excel de plantilla del proceso/entrada indicado."""
    proceso = _proceso_por_id(tipo)
    if proceso is None:
        abort(404)
    entrada = next((e for e in proceso["entradas"] if e["clave"] == clave), None)
    if entrada is None:
        abort(404)
    archivo = entrada["archivo"]
    if not os.path.exists(os.path.join(BASE_DIR, archivo)):
        abort(404)
    return send_from_directory(BASE_DIR, archivo, as_attachment=True)


def _mensaje_amigable(exc):
    """Traduce las excepciones más comunes a un mensaje claro para el usuario."""
    texto = str(exc)
    tipo = type(exc).__name__

    if isinstance(exc, KeyError):
        return f"Falta la columna {texto} en el Excel (revisa el encabezado de la hoja)."
    if isinstance(exc, ValueError) and "Worksheet" in texto:
        return f"No se encontró la hoja indicada en el Excel: {texto}."
    if isinstance(exc, IndexError):
        return "Faltan filas de datos en el Excel (revisa que la hoja tenga registros)."
    if isinstance(exc, FileNotFoundError):
        return "No se pudo leer el archivo. Vuelve a subirlo."
    return f"{tipo}: {texto}"


def _llamar_procesador(modulo, entrada, work_dir, empresa_id, fecha, parametros, datos):
    """Invoca ``modulo.procesar`` pasando solo los argumentos que acepta."""
    params = inspect.signature(modulo.procesar).parameters
    kwargs = {}
    if "empresa_id" in params:
        kwargs["empresa_id"] = empresa_id
    if "fecha" in params:
        kwargs["fecha"] = fecha
    if "parametros" in params:
        kwargs["parametros"] = parametros
    if "datos" in params:
        kwargs["datos"] = datos
    return modulo.procesar(entrada, work_dir, **kwargs)


def _ejecutar_proceso(modulo, tipo, entrada, empresa_id, fecha, parametros, datos):
    """Ejecuta un procesador y devuelve la respuesta JSON de Flask."""
    with tempfile.TemporaryDirectory(prefix="siesa_") as work_dir:
        try:
            resultado = _llamar_procesador(modulo, entrada, work_dir, empresa_id, fecha, parametros, datos)
        except Exception as exc:  # noqa: BLE001 - se reporta al usuario
            detalle = traceback.format_exc()
            app.logger.error("Error procesando %s: %s", tipo, detalle)
            return jsonify({
                "ok": False,
                "mensaje": _mensaje_amigable(exc),
                "tipo_error": type(exc).__name__,
                "detalle": detalle,
            }), 500

    exito = resultado.get("ok", False)
    return jsonify({
        "ok": exito,
        "mensaje": "Proceso ejecutado correctamente." if exito
        else f"El servicio respondió con código {resultado.get('status_code')}.",
        "status_code": resultado.get("status_code"),
        "registros": resultado.get("registros"),
        "respuesta": resultado.get("respuesta"),
        "trama_txt": resultado.get("trama_txt"),
        "trama_nombre": resultado.get("trama_nombre"),
    }), (200 if exito else 502)


@app.route("/api/procesar/<tipo>", methods=["POST"])
def procesar(tipo):
    modulo = PROCESADORES.get(tipo)
    proceso = _proceso_por_id(tipo)
    if proceso is None:
        return jsonify({"ok": False, "mensaje": f"Proceso no válido: {tipo}"}), 404
    if modulo is None:
        return jsonify({
            "ok": False,
            "mensaje": f"El proceso '{proceso['nombre']}' aún no está disponible en la web.",
        }), 501

    # Empresa (obligatoria si el proceso la requiere).
    empresa_id = (request.form.get("empresa") or "").strip()
    if proceso.get("requiere_empresa") and not empresa_valida(empresa_id):
        return jsonify({"ok": False, "mensaje": "Selecciona una empresa válida."}), 400

    # Fecha (obligatoria si el proceso la requiere), formato AAAAMMDD.
    fecha = (request.form.get("fecha") or "").strip()
    if proceso.get("requiere_fecha"):
        if len(fecha) != 8 or not fecha.isdigit():
            return jsonify({"ok": False, "mensaje": "Indica la fecha en formato AAAAMMDD."}), 400

    # Modo de parámetros: 'excel' (todo del Excel) o 'manual' (todo escrito a mano).
    parametros = None
    datos = None
    modo = (request.form.get("modo_parametros") or "excel").strip()
    if modo == "manual":
        if not admite_parametros_manuales(tipo):
            return jsonify({"ok": False, "mensaje": "Este proceso no admite datos manuales."}), 400

        # Parámetros escritos a mano.
        parametros = {}
        faltan_campos = []
        for campo in esquema_de(tipo):
            valor = (request.form.get(f"param_{campo['clave']}") or "").strip()
            if not valor:
                faltan_campos.append(campo["etiqueta"])
            parametros[campo["clave"]] = valor
        if faltan_campos:
            return jsonify({
                "ok": False,
                "mensaje": "Faltan parámetros: " + ", ".join(faltan_campos) + ".",
            }), 400

        # Registros de datos escritos a mano (uno o varios).
        esquema_datos = datos_esquema_de(tipo)
        try:
            registros = json.loads(request.form.get("datos") or "[]")
        except ValueError:
            return jsonify({"ok": False, "mensaje": "Los registros de datos no son válidos."}), 400
        if not isinstance(registros, list) or not registros:
            return jsonify({"ok": False, "mensaje": "Agrega al menos un registro de datos."}), 400

        datos = []
        for idx, reg in enumerate(registros, start=1):
            fila = {}
            for campo in esquema_datos:
                valor = str(reg.get(campo["clave"], "")).strip()
                if valor == "":
                    # Solo son obligatorias las columnas que el proceso usa/envía.
                    if campo.get("usado"):
                        return jsonify({"ok": False, "mensaje": f"Registro {idx}: falta '{campo['etiqueta']}'."}), 400
                    continue  # columna opcional vacía: se omite
                if campo["tipo"] == "number":
                    try:
                        valor = float(valor)
                    except ValueError:
                        return jsonify({"ok": False, "mensaje": f"Registro {idx}: '{campo['etiqueta']}' debe ser numérico."}), 400
                fila[campo["clave"]] = valor
            datos.append(fila)

    # En modo manual no se sube Excel: se procesa directamente con los datos.
    if modo == "manual":
        return _ejecutar_proceso(modulo, tipo, None, empresa_id, fecha, parametros, datos)

    entradas = proceso["entradas"]

    # Valida que se hayan recibido todos los archivos requeridos por el proceso.
    faltantes = [e for e in entradas
                 if e["clave"] not in request.files or not request.files[e["clave"]].filename]
    if faltantes:
        nombres = ", ".join(e["etiqueta"] for e in faltantes)
        return jsonify({"ok": False, "mensaje": f"Falta cargar: {nombres}."}), 400

    for entrada in entradas:
        archivo = request.files[entrada["clave"]]
        if not _extension_valida(archivo.filename):
            return jsonify({
                "ok": False,
                "mensaje": f"'{entrada['etiqueta']}': formato no permitido. Sube un Excel (.xlsx, .xlsm, .xls).",
            }), 400

    with tempfile.TemporaryDirectory(prefix="siesa_upload_") as up_dir:
        rutas = {}
        for entrada in entradas:
            archivo = request.files[entrada["clave"]]
            nombre_seguro = secure_filename(archivo.filename)
            ruta = os.path.join(up_dir, f"{entrada['clave']}_{nombre_seguro}")
            archivo.save(ruta)
            rutas[entrada["clave"]] = ruta

        # Procesos de un solo archivo reciben la ruta directa; los de varios, el diccionario.
        entrada_proc = rutas[entradas[0]["clave"]] if len(entradas) == 1 else rutas
        return _ejecutar_proceso(modulo, tipo, entrada_proc, empresa_id, fecha, parametros, datos)


@app.errorhandler(413)
def archivo_muy_grande(_error):
    return jsonify({"ok": False, "mensaje": "El archivo supera el tamaño máximo permitido (25 MB)."}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

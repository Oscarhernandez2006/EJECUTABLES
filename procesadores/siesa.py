"""Utilidades compartidas para la integración con el servicio web de Siesa.

Contiene la lógica común de generación de consecutivos, guardado de la trama,
construcción del XML de importación y consumo del servicio SOAP.
"""

import os
import re
from xml.etree.ElementTree import Element, SubElement, tostring

import pandas as pd
import requests

# Endpoint del servicio web de Siesa (común a todos los procesos).
URL_SERVICIO = "https://wscarnesantacruz.siesacloud.com:8043/wsUNOEE/wsUNOEE.asmx"
NOMBRE_CONEXION = "UnoEE_Carnesantacruz_Real"

# Credenciales del servicio web de Siesa. En producción defínelas por variables
# de entorno (Dokploy): SIESA_USER y SIESA_PASSWORD. El valor por defecto se deja
# solo por compatibilidad y DEBE rotarse (quedó expuesto en el repositorio).
SIESA_USER = os.getenv("SIESA_USER", "webservices")
SIESA_PASSWORD = os.getenv("SIESA_PASSWORD", "Santacruz2026*")

# Raíz del proyecto y archivo de referencias FRIGOAPP -> Siesa (constante entre
# empresas). Empaquetado junto a la aplicación para procesos que lo requieren
# (cargue de lotes, canales, retomas, documentos de pedidos).
RUTA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_REFERENCIAS = os.path.join(RUTA_PROYECTO, "CODIGO SIESA.xlsx")


def validar_empresa(cia_excel, empresa_id):
    """Verifica que la compañía del Excel coincida con la empresa seleccionada.

    Los ejecutables toman la CIA del propio Excel; el selector de empresa de la
    web actúa como salvaguarda para no procesar el archivo de otra compañía.
    Lanza ``ValueError`` si no coinciden.
    """
    if not empresa_id:
        return
    try:
        cia_norm = str(int(float(cia_excel)))
    except (TypeError, ValueError):
        cia_norm = str(cia_excel).strip()
    if cia_norm != str(empresa_id):
        raise ValueError(
            f"El archivo pertenece a {_nombre_empresa(cia_norm)} pero seleccionaste "
            f"{_nombre_empresa(empresa_id)}. Verifica el archivo o la empresa elegida."
        )


def _nombre_empresa(cia):
    """Nombre legible de una compañía por su CIA; cae al número si no está en el catálogo."""
    try:
        from config.empresas import obtener_empresa
        emp = obtener_empresa(str(cia))
        if emp:
            return f"{emp['corto']} ({cia})"
    except Exception:
        pass
    return f"la compañía {cia}"


def exigir_datos(df, mensaje):
    """Lanza un ``ValueError`` legible si el DataFrame quedó sin filas.

    Evita tramas vacías (que Siesa rechaza con "No existen datos para procesar")
    y los ``IndexError`` al leer la primera fila de un archivo/filtro vacío.
    """
    if df is None or len(df) == 0:
        raise ValueError(mensaje)


def param_por_nombre(df, texto, col_nombre="PARAMETRO", col_valor="CODIGO_PARAMETRO"):
    """Busca en la hoja PARAMETROS la fila cuyo nombre contenga ``texto``.

    Devuelve el valor de la columna de código, o ``None`` si no la encuentra.
    Útil para parámetros que el ejecutable no leía por posición fija.
    """
    mask = df[col_nombre].astype(str).str.upper().str.contains(texto.upper(), na=False)
    filtrado = df[mask]
    if filtrado.empty:
        return None
    return filtrado[col_valor].iloc[0]


def leer_datos_canal(datos, excel_path, dtype=None, skiprows=6, sheet="CANAL"):
    """Devuelve el DataFrame de datos: de registros manuales o del Excel.

    Si ``datos`` (lista de dicts) no es ``None``, construye el DataFrame a
    partir de esos registros; de lo contrario lee la hoja indicada del Excel.
    """
    if datos is not None:
        return pd.DataFrame(datos)
    return pd.read_excel(excel_path, sheet_name=sheet, dtype=dtype, skiprows=skiprows)


def hoja_df(hojas, clave, dtype=None):
    """Construye el DataFrame de una hoja manual (lista de dicts) por su clave.

    ``hojas`` es el dict {nombre_hoja: [registros]} que llega del modo manual
    por hojas. Aplica ``dtype`` a las columnas presentes.
    """
    registros = (hojas or {}).get(clave, []) or []
    df = pd.DataFrame(registros)
    if dtype:
        for col, tipo in dtype.items():
            if col in df.columns:
                df[col] = df[col].astype(tipo)
    return df


def generar_cons(i, t):
    """Genera un consecutivo de ``t`` dígitos rellenado con ceros a la izquierda."""
    tamano = "0" * t
    n_car = len(str(i))
    return str(tamano[0:(len(tamano) - n_car)] + str(i))


def generar_consecutivo(i):
    """Genera un consecutivo de 7 dígitos rellenado con ceros a la izquierda."""
    return generar_cons(i, 7)


def guardar_trama(filas, ruta_archivo):
    """Escribe cada línea de la trama en un archivo de texto plano."""
    with open(ruta_archivo, "w") as archivo:
        for fila in filas:
            archivo.write("".join(str(fila)) + "\n")
    return ruta_archivo


def generar_xml(txt_path, xml_path, cia_conexion, usuario=None, clave=None):
    """Construye el XML de importación a partir de la trama de texto."""
    usuario = usuario or SIESA_USER
    clave = clave or SIESA_PASSWORD
    importar = Element("Importar")

    nombre_conexion = SubElement(importar, "NombreConexion")
    nombre_conexion.text = NOMBRE_CONEXION

    id_cia = SubElement(importar, "IdCia")
    id_cia.text = cia_conexion

    usuario_el = SubElement(importar, "Usuario")
    usuario_el.text = usuario

    clave_el = SubElement(importar, "Clave")
    clave_el.text = clave

    datos = SubElement(importar, "Datos")
    with open(txt_path, "r") as archivo:
        for linea in archivo:
            linea_elemento = SubElement(datos, "Linea")
            linea_elemento.text = linea

    xml_content = tostring(importar, encoding="utf-8").decode("utf-8")

    with open(xml_path, "w") as xml_file:
        xml_file.write(xml_content)

    return xml_path


def consumir_servicio_web(xml_path, url=URL_SERVICIO):
    """Envía el XML al servicio web SOAP y devuelve un diccionario con el resultado.

    El resultado incluye:
      - ``ok``: True solo si HTTP 200, sin SOAP Fault y sin marcadores de error
        en la respuesta de Siesa (para no dar por bueno un error de negocio o
        de autenticación que Siesa devuelve con código 200).
      - ``status_code``: código HTTP.
      - ``respuesta``: texto SOAP completo (para depuración).
      - ``mensaje``: mensaje legible extraído de Siesa (o del fault/red).
      - ``error``: bandera booleana de error.
    """
    with open(xml_path, "r") as f:
        xml_content = f.read()

    soap_body = """
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
       <soapenv:Header/>
       <soapenv:Body>
          <tem:ImportarXML>
             <tem:pvstrDatos><![CDATA[{xml_content}]]></tem:pvstrDatos>
             <tem:printTipoError>0</tem:printTipoError>
          </tem:ImportarXML>
       </soapenv:Body>
    </soapenv:Envelope>
    """.format(xml_content=xml_content)

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/ImportarXML",
    }

    # Errores de red/timeout no revientan el proceso: se reportan estructurados.
    try:
        response = requests.post(url, data=soap_body, headers=headers, timeout=120)
    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "respuesta": "",
            "mensaje": f"No se pudo conectar con el servicio de Siesa: {exc}",
            "error": True,
        }

    texto = response.text or ""
    fault = _extraer_fault(texto)
    resultado_siesa = _extraer_resultado_siesa(texto)

    hay_error = (
        response.status_code != 200
        or fault is not None
        or _resultado_es_error(resultado_siesa)
    )

    # Mensaje legible para el usuario (sin etiquetas XML ni "texto todo junto").
    limpio = _limpiar_mensaje(resultado_siesa)
    if not hay_error:
        if limpio and len(limpio) <= 200:
            mensaje = "Importación registrada en Siesa. " + limpio
        else:
            mensaje = "Importación registrada correctamente en Siesa."
    elif fault:
        mensaje = "Siesa rechazó la importación: " + (_limpiar_mensaje(fault) or "error del servicio.")
    else:
        mensaje = "Siesa reportó un error: " + (limpio[:400] or f"código {response.status_code}.")

    return {
        "ok": not hay_error,
        "status_code": response.status_code,
        "respuesta": texto,
        "mensaje": mensaje.strip(),
        "error": hay_error,
    }


# Marcadores típicos de error en la respuesta de Siesa (heurística conservadora).
_MARCADORES_ERROR = (
    "error", "no se pudo", "inv\u00e1lid", "invalid", "incorrect", "fall\u00f3",
    "excepc", "denied", "no autoriz", "rechaz", "no existe", "obligatori",
)


def _extraer_resultado_siesa(texto):
    """Extrae y desescapa el contenido de <ImportarXMLResult> del SOAP."""
    m = re.search(r"<ImportarXMLResult>(.*?)</ImportarXMLResult>", texto, re.DOTALL)
    if not m:
        return None
    val = m.group(1)
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")):
        val = val.replace(a, b)
    return val.strip()


def _extraer_fault(texto):
    """Extrae el <faultstring> de un SOAP Fault, si lo hay."""
    m = re.search(r"<faultstring>(.*?)</faultstring>", texto, re.DOTALL)
    return m.group(1).strip() if m else None


def _resultado_es_error(resultado):
    """Heurística: True si el texto de Siesa contiene marcadores de error."""
    if not resultado:
        return False
    bajo = resultado.lower()
    return any(marca in bajo for marca in _MARCADORES_ERROR)


def _limpiar_mensaje(texto):
    """Convierte la respuesta de Siesa (a veces XML) en texto legible.

    Quita etiquetas, desescapa entidades y colapsa espacios para que el mensaje
    se lea como una frase y no como un bloque de texto pegado.
    """
    if not texto:
        return ""
    sin_tags = re.sub(r"<[^>]+>", " ", texto)
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")):
        sin_tags = sin_tags.replace(a, b)
    sin_tags = re.sub(r"<[^>]+>", " ", sin_tags)
    return re.sub(r"\s+", " ", sin_tags).strip()

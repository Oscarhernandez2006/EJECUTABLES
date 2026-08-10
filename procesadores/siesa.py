"""Utilidades compartidas para la integración con el servicio web de Siesa.

Contiene la lógica común de generación de consecutivos, guardado de la trama,
construcción del XML de importación y consumo del servicio SOAP.
"""

import os
from xml.etree.ElementTree import Element, SubElement, tostring

import pandas as pd
import requests

# Endpoint del servicio web de Siesa (común a todos los procesos).
URL_SERVICIO = "https://wscarnesantacruz.siesacloud.com:8043/wsUNOEE/wsUNOEE.asmx"
NOMBRE_CONEXION = "UnoEE_Carnesantacruz_Real"

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
            f"El archivo es de la compañía {cia_norm} pero seleccionaste la "
            f"empresa {empresa_id}. Verifica el archivo o la empresa elegida."
        )


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


def generar_xml(txt_path, xml_path, cia_conexion, usuario, clave):
    """Construye el XML de importación a partir de la trama de texto."""
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
    """Envía el XML al servicio web SOAP y devuelve un diccionario con el resultado."""
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

    response = requests.post(url, data=soap_body, headers=headers, timeout=120)

    return {
        "ok": response.status_code == 200,
        "status_code": response.status_code,
        "respuesta": response.text,
    }

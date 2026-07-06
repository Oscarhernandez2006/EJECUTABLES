"""Utilidades compartidas para la integración con el servicio web de Siesa.

Contiene la lógica común de generación de consecutivos, guardado de la trama,
construcción del XML de importación y consumo del servicio SOAP.
"""

import os
from xml.etree.ElementTree import Element, SubElement, tostring

import requests

# Endpoint del servicio web de Siesa (común a todos los procesos).
URL_SERVICIO = "https://wscarnesantacruz.siesacloud.com:8043/wsUNOEE/wsUNOEE.asmx"
NOMBRE_CONEXION = "UnoEE_Carnesantacruz_Real"


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

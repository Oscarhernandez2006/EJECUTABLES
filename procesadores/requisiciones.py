"""Procesador de Requisiciones (transferencias) para Siesa.

Lee la hoja 'TRASNFERENCIA' del Excel cargado, genera la trama de importación
(tipos de registro 440/441) y la envía al servicio web de Siesa.
"""

import os

import pandas as pd

from . import siesa

# Credenciales del servicio web (configurables por variables de entorno).
USER = os.getenv("SIESA_REQUISICIONES_USER", "webservices")
PASSWORD = os.getenv("SIESA_REQUISICIONES_PASSWORD", "Santacruz2026*")


class Req:
    def __init__(self, excel_path, work_dir):
        self.excel_path = excel_path
        self.work_dir = work_dir

        self.Req = pd.read_excel(
            excel_path, sheet_name="TRASNFERENCIA",
            dtype={"N.I.T / C.C.": str, "CODIGO": str, "BOD ENTRADA": str, "BOD SALIDA": str},
        )
        self.EQUIVALENCIA = pd.read_excel(
            excel_path, sheet_name="EQUIVALENTES",
            dtype={"CODIGO": str, "REF_SIESA": str}, skiprows=1,
        )
        self.data2 = pd.read_excel(
            excel_path, sheet_name="PARAMETROS",
            dtype={"CODIGO_PARAMETRO": str, "REF_SIESA": str}, skiprows=1,
        )
        self.d0 = []

        self.CIA = self.data2["CODIGO_PARAMETRO"].iloc[0]
        self.CO = self.data2["CODIGO_PARAMETRO"].iloc[1]
        self.TERCERO = self.data2["CODIGO_PARAMETRO"].iloc[2]
        self.SOLICITANTE = self.data2["CODIGO_PARAMETRO"].iloc[3]
        self.UN = self.data2["CODIGO_PARAMETRO"].iloc[4]
        self.CCOSTOS = self.data2["CODIGO_PARAMETRO"].iloc[5]
        self.FECHA = self.data2["CODIGO_PARAMETRO"].iloc[6]
        self.CO_SALIDA = self.data2["CODIGO_PARAMETRO"].iloc[10]

        self.MOTIVO = "02"
        self.TIPO_DOC = "RQI"
        self.CONCEPTO = "605"
        self.CLASE_DOCUMENTO = "76"

        self.CIA_CONEXION = str(int(self.CIA))

    def crear_dataframes(self):
        self.CIA = int(self.CIA)
        self.Req["Número de documento"] = self.Req["NUM_DOC"]
        map_ref_siesa = dict(zip(self.EQUIVALENCIA["CODIGO"], self.EQUIVALENCIA["REF_SIESA"]))
        self.Req["REF_SIESA"] = self.Req["CODIGO"].map(map_ref_siesa)
        self.Req2 = self.Req.copy()
        self.Req.drop_duplicates("Número de documento", keep="first", inplace=True)

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + str("{:0>3.0f}".format(self.CIA))
        self.d0.append(self.trama)
        c = 2
        t = 7
        for indice, fila in self.Req.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(440)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:0>1.0f}".format(1)
                + "{:3}".format(self.CO)
                + "{:3}".format(self.TIPO_DOC)
                + "{:0>8.0f}".format(fila["NUM_DOC"])
                + "{:8}".format(self.FECHA)
                + "{:15}".format(" ")
                + "{:5}".format(self.SOLICITANTE)
                + "{:8}".format(self.FECHA)
                + "{:0>3.0f}".format(1)
                + "{:3}".format(self.CLASE_DOCUMENTO)
                + "{:0>1.0f}".format(0)
                + "{:0>1.0f}".format(0)
                + "{:255}".format(" ")
                + "{:3}".format(self.CONCEPTO)
                + "{:5}".format(fila["BOD ENTRADA"])
                + "{:5}".format(fila["BOD SALIDA"])
                + "{:20}".format(" ")
                + "{:10}".format(" ")
            )
            self.d0.append(row)
            c = c + 1
        ci = 1
        for indice, fila in self.Req2.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(441)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:3}".format(self.CO)
                + "{:3}".format(self.TIPO_DOC)
                + "{:0>8.0f}".format(fila["Número de documento"])[:8]
                + "{:0>10.0f}".format(fila["No."])[:10]
                + "{:0>7.0f}".format(0)
                + "{:50}".format(fila["REF_SIESA"])
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:5}".format(fila["BOD ENTRADA"])
                + "{:3}".format(self.CONCEPTO)
                + "{:2}".format(self.MOTIVO)
                + "{:<4}".format("KG")
                + "{:0>20.4f}".format(fila["CANT.(kg)"])
                + "{:0>20.4f}".format(0)
                + "{:8}".format(self.FECHA)
                + "{:0>3.0f}".format(1)
                + "{:3}".format(self.CO)
                + "{:0>2}".format(" ")
                + "{:15}".format(" ")
                + "{:15}".format(" ")
                + "{:255}".format(" ")
                + "{:2000}".format(" ")
                + "{:20}".format(self.UN)
            )
            self.d0.append(row)
            c = c + 1
            ci = ci + 1
        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + str("{:0>3.0f}".format(self.CIA))
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir):
    """Ejecuta el flujo completo de Requisiciones y devuelve el resultado."""
    proc = Req(excel_path, work_dir)
    proc.crear_dataframes()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "Req.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.Req2)
    return resultado

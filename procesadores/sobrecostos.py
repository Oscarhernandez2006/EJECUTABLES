"""Procesador de Sobrecostos para Siesa.

Lee la hoja 'SOBRECOSTOS' del Excel cargado, genera la trama de importación
(tipos de registro 451/452) y la envía al servicio web de Siesa.
"""

import os

import pandas as pd

from . import siesa

# Credenciales del servicio web (configurables por variables de entorno).
USER = os.getenv("SIESA_SOBRECOSTOS_USER", "webservices")
PASSWORD = os.getenv("SIESA_SOBRECOSTOS_PASSWORD", "Santacruz2026*")


class Sobrecosto:
    def __init__(self, excel_path, work_dir):
        self.excel_path = excel_path
        self.work_dir = work_dir

        self.Ped = pd.read_excel(
            excel_path, sheet_name="SOBRECOSTOS",
            dtype={"N.I.T / C.C.": str, "CODIGO": str, "BOD ENTRADA": str,
                   "BOD SALIDA": str, "SUCURSAL": str},
            skiprows=1,
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
        self.VENDEDOR = self.data2["CODIGO_PARAMETRO"].iloc[7]
        self.LISTA_PRECIO = self.data2["CODIGO_PARAMETRO"].iloc[8]
        self.COMPRADOR = self.data2["CODIGO_PARAMETRO"].iloc[9]

        self.MOTIVO = "01"
        self.CONCEPTO = "402"
        self.TIP_DOC = "AJS"
        self.TIPO_PROVEEDOR = "0001"
        self.CLASE_DOCUMENTO = "410"
        self.MODO_LIQUIDACION_COSTO = 1
        self.REFERENCIA_SOBRECOSTO = "1520"
        self.UM = "U"

        self.CIA_CONEXION = str(int(self.CIA))

    def crear_dataframes(self):
        self.CIA = int(self.CIA)
        self.Ped2 = self.Ped.copy()

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + str("{:0>3.0f}".format(self.CIA))
        self.d0.append(self.trama)
        c = 2
        t = 7
        for indice, fila in self.Ped.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(451)
                + "{:0>2.0f}".format(1)
                + "{:0>2.0f}".format(1)
                + "{:0>3.0f}".format(self.CIA)
                + "{:0>1.0f}".format(1)
                + "{:0>1.0f}".format(1)
                + "{:3}".format(self.CO)
                + "{:3}".format(self.TIP_DOC)
                + "{:0>8.0f}".format(fila["NUM_DOC"])
                + "{:8}".format(self.FECHA)
                + "{:15}".format(fila["N.I.T / C.C."])
                + "{:3}".format(self.CLASE_DOCUMENTO)
                + "{:0>1.0f}".format(0)
                + "{:0>1.0f}".format(0)
                + "{:255}".format(" ")
                + "{:3}".format(self.CONCEPTO)
                + "{:3}".format(self.CLASE_DOCUMENTO)
                + "{:3}".format(fila["SUCURSAL"])
                + "{:15}".format(self.COMPRADOR)
                + "{:0>12.0f}".format(fila["NUM_DOC"])
                + "{:3}".format("COP")
                + "{:3}".format("COP")
                + "{:0>13.4f}".format(1)
                + "{:3}".format("COP")
                + "{:0>13.4f}".format(1)
                + "{:3}".format(fila["TIPO_DOC_BASE"])
                + "{:0>8.0f}".format(fila["NUM_DOC_BASE"])
                + "{:2}".format(self.MOTIVO)
                + "{:0>1.0f}".format(self.MODO_LIQUIDACION_COSTO)
                + "{:10}".format(" ")
                + "{:15}".format(" ")
                + "{:3}".format(" ")
                + "{:15}".format(" ")
                + "{:50}".format(" ")
                + "{:15}".format(" ")
                + "{:30}".format(" ")
                + "{:0>15.4f}".format(0)
                + "{:0>20.4f}".format(0)
                + "{:0>20.4f}".format(0)
                + "{:0>20.4f}".format(0)
                + "{:255}".format(" ")
            )
            self.d0.append(row)
            c = c + 1
        ci = 1
        for indice, fila in self.Ped2.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(452)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:3}".format(self.CO)
                + "{:3}".format(self.TIP_DOC)
                + "{:0>8.0f}".format(fila["NUM_DOC"])
                + "{:0>10.0f}".format(fila["NUM_DOC"])
                + "{:47}".format(" ")
                + "{:0>20.4f}".format(fila["VALOR"])
                + "{:3}".format(" ")
                + "{:40}".format(fila["DESCRIPCION"])
                + "{:4}".format(self.UM)
                + "{:0>7.0f}".format(0)
                + "{:<50}".format(fila["REF_SOBRECOSTOS"])
                + "{:20}".format(" ")
            )
            self.d0.append(row)
            c = c + 1
            ci = ci + 1
        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + str("{:0>3.0f}".format(self.CIA))
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir):
    """Ejecuta el flujo completo de Sobrecostos y devuelve el resultado."""
    proc = Sobrecosto(excel_path, work_dir)
    proc.crear_dataframes()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "SOBRE_COSTOS.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.Ped2)
    return resultado

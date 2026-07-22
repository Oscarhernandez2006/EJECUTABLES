"""Procesador de Cruce Contable (reclasificación de compra) para Siesa.

Lee la hoja 'CANAL' del Excel de análisis cargado (junto con 'PARAMETROS' y
'PARAMETROS ITEMS'), genera la trama contable (tipos de registro 350/351) con
el asiento débito/crédito por el valor total y la envía al servicio web.

Nota: la versión de escritorio pedía la fecha con una ventana Tkinter. En la
versión web se toma automáticamente la fecha de la hoja CANAL
('FECHA SACRIFICIO SIESA', primera fila).
"""

import os

import pandas as pd

from . import siesa

# Credenciales del servicio web (configurables por variables de entorno).
USER = os.getenv("SIESA_CRUCE_USER", "webservices")
PASSWORD = os.getenv("SIESA_CRUCE_PASSWORD", "Santacruz2026*")


class FacturaCompra:
    def __init__(self, excel_path, work_dir):
        self.excel_path = excel_path
        self.work_dir = work_dir

        self.data1 = pd.read_excel(
            excel_path, sheet_name="CANAL",
            dtype={"NIT PROVEEDOR": str, "FECHA SACRIFICIO SIESA": str, "LOTE": str},
            skiprows=6,
        )
        self.data2 = pd.read_excel(
            excel_path, sheet_name="PARAMETROS",
            dtype={"CO": str, "BODEGA": str, "UN": str},
        )
        self.data3 = pd.read_excel(
            excel_path, sheet_name="PARAMETROS ITEMS",
            dtype={"CODIGO_PARAMETRO": str},
        )

        # Fecha tomada de la hoja CANAL (primera fila).
        self.fecha = self.data1["FECHA SACRIFICIO SIESA"].iloc[0]

        self.CIA = self.data2["CODIGO_PARAMETRO"].iloc[0]
        self.CO = str(int(self.data2["CODIGO_PARAMETRO"].iloc[1]))
        self.COMPRADOR = self.data2["CODIGO_PARAMETRO"].iloc[4]
        self.UN = self.data2["UN"].iloc[5]

        self.SERVICIO_COMPRA = str(int(self.data3["CODIGO_PARAMETRO"].iloc[0]))
        self.TIPO_DOCUMENTO = "NI"
        self.MONEDA = "COP"
        self.REFERENCIA = "1678"
        self.TERCERO = "Generico"
        self.AUXLIAR_DB_VACUNO = self.data2["CODIGO_PARAMETRO"].iloc[13]
        self.AUXLIAR_DB_PORCINO = self.data2["CODIGO_PARAMETRO"].iloc[14]
        self.AUXILIAR_CR_VACUNO = self.data2["CODIGO_PARAMETRO"].iloc[15]
        self.AUXILIAR_CR_PORCINO = self.data2["CODIGO_PARAMETRO"].iloc[16]
        self.TERCERO_CRE = "Generico"
        self.d0 = []

        self.CIA_CONEXION = str(int(self.CIA))

    def dataframe(self):
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]
        self.data1 = self.data1.loc[
            self.data1["FECHA SACRIFICIO SIESA"] == str(self.fecha)
        ].copy()
        self.data1["VR_COMPRA"] = self.data1["Total a facturar"].round(2)
        self.VALOR_TOTAL = self.data1["VR_COMPRA"].sum()

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)

        # Encabezado del documento (registro 350).
        row = (
            "0000002"
            + "{:0>4.0f}".format(350)
            + "{:0>2.0f}".format(0)
            + "{:0>2.0f}".format(1)
            + "{:0>3.0f}".format(self.CIA)
            + "{:0>1.0f}".format(1)
            + "{:3}".format(self.CO)
            + "{:3}".format(self.TIPO_DOCUMENTO)
            + "{:0>8.0f}".format(1)
            + "{:8}".format(self.fecha)
            + "{:<15}".format(self.TERCERO)
            + "{:5}".format("30")
            + "{:0>1.0f}".format(1)
            + "{:0>1.0f}".format(0)
            + "{:255}".format(" ")
        )
        self.d0.append(row)

        # Movimiento contable débito (registro 351).
        row = (
            "0000003"
            + "{:0>4.0f}".format(351)
            + "{:0>2.0f}".format(0)
            + "{:0>2.0f}".format(2)
            + "{:0>3.0f}".format(self.CIA)
            + "{:3}".format(self.CO)
            + "{:3}".format(self.TIPO_DOCUMENTO)
            + "{:0>8.0f}".format(1)
            + "{:20}".format(
                self.AUXLIAR_DB_VACUNO if self.SERVICIO_COMPRA == "1690"
                else self.AUXLIAR_DB_PORCINO)
            + "{:<15}".format(self.TERCERO_CRE)
            + "{:3}".format(self.CO)
            + "{:<20}".format(self.UN)
            + "{:<15}".format(" ")
            + "{:<10}".format(" ")
            + "+" + "{:0>20.4f}".format(self.VALOR_TOTAL)
            + "+" + "{:0>20.4f}".format(0)
            + "+" + "{:0>20.4f}".format(0)
            + "+" + "{:0>20.4f}".format(0)
            + "+" + "{:0>20.4f}".format(0)
            + "{:2}".format(" ")
            + "{:0>8.0f}".format(0)
            + "{:255}".format(" ")
        )
        self.d0.append(row)

        # Movimiento contable crédito (registro 351).
        row = (
            "0000004"
            + "{:0>4.0f}".format(351)
            + "{:0>2.0f}".format(0)
            + "{:0>2.0f}".format(2)
            + "{:0>3.0f}".format(self.CIA)
            + "{:3}".format(self.CO)
            + "{:3}".format(self.TIPO_DOCUMENTO)
            + "{:0>8.0f}".format(1)
            + "{:20}".format(
                self.AUXILIAR_CR_VACUNO if self.SERVICIO_COMPRA == "1690"
                else self.AUXILIAR_CR_PORCINO)
            + "{:<15}".format(self.TERCERO_CRE)
            + "{:3}".format(self.CO)
            + "{:<20}".format(self.UN)
            + "{:<15}".format(" ")
            + "{:<10}".format(" ")
            + "+" + "{:0>20.4f}".format(0)
            + "+" + "{:0>20.4f}".format(self.VALOR_TOTAL)
            + "+" + "{:0>20.4f}".format(0)
            + "+" + "{:0>20.4f}".format(0)
            + "+" + "{:0>20.4f}".format(0)
            + "{:2}".format(" ")
            + "{:0>8.0f}".format(0)
            + "{:255}".format(" ")
        )
        self.d0.append(row)

        self.trama_final = "0000005" + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir):
    """Ejecuta el flujo completo de Cruce Contable y devuelve el resultado."""
    proc = FacturaCompra(excel_path, work_dir)
    proc.dataframe()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "Reclasificacion_Compra.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.data1)
    return resultado

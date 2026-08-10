"""Procesador de Flete Bovino para Siesa (documento EAC).

Portado desde ``5.-FLETE_BOVINO.py``. Genera la factura de fletes de transporte
de ganado (registros 451 y 470). El proveedor es el 'NIT PROVEEDOR FLETE' y el
valor es 'flete*animal'. Conserva intacta la lógica de trama.
"""

import os

import pandas as pd

from . import siesa

USER = siesa.SIESA_USER
PASSWORD = siesa.SIESA_PASSWORD

MOTIVO = "01"
TIPO_DOCUMENTO = "EAC"
MONEDA = "COP"


class FleteBovino:
    def __init__(self, excel_path, work_dir, empresa_id, fecha, parametros=None, datos=None):
        self.excel_path = excel_path
        self.work_dir = work_dir
        self.fecha = fecha

        if parametros:
            self.CIA = int(empresa_id)
            self.CO = str(parametros["CO"])
            self.BODEGA = str(parametros["BODEGA"])
            self.COMPRADOR = str(parametros["COMPRADOR"])
            self.UN = str(parametros["UN"])
        else:
            # Parámetros de la hoja PARAMETROS, igual que el ejecutable.
            self.data2 = pd.read_excel(
                excel_path, sheet_name="PARAMETROS",
                dtype={"CO": str, "BODEGA": str, "UN": str})
            self.CIA = self.data2["CODIGO_PARAMETRO"].iloc[0]
            self.CO = self.data2["CODIGO_PARAMETRO"].iloc[1]
            self.BODEGA = self.data2["CODIGO_PARAMETRO"].iloc[2]
            self.COMPRADOR = self.data2["CODIGO_PARAMETRO"].iloc[4]
            self.UN = self.data2["UN"].iloc[5]
            siesa.validar_empresa(self.CIA, empresa_id)
        self.CIA_CONEXION = str(int(self.CIA))

        self.data1 = siesa.leer_datos_canal(
            datos, excel_path,
            dtype={"NIT": str, "FECHA SACRIFICIO SIESA": str, "NIT PROVEEDOR FLETE": str},
            skiprows=6,
        )
        self.d0 = []

    def dataframe(self):
        self.data1["Fecha_control"] = ""
        self.data1 = self.data1[self.data1["NIT PROVEEDOR FLETE"].notna()]
        self.data1["NUMERO_DOC"] = 0
        for i, _ in self.data1.iterrows():
            self.data1.at[i, "NUMERO_DOC"] = i + 1
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]
        self.data1 = self.data1[self.data1["FECHA SACRIFICIO SIESA"] == self.fecha]
        self.data1 = self.data1[self.data1["PESO EN FINCA"] > 0]
        self.data1["flete*animal"] = self.data1["flete*animal"].round(0)

    def consecutivo_documento(self):
        self.enc_data1 = self.data1.copy()
        self.enc_data1["NUMERO_DOC"] = 0
        self.enc_data1.drop_duplicates("NIT PROVEEDOR FLETE", inplace=True)
        for i, _ in self.enc_data1.iterrows():
            self.enc_data1.at[i, "NUMERO_DOC"] = i + 1
        map_num_doc = dict(zip(self.enc_data1["NIT PROVEEDOR FLETE"], self.enc_data1["NUMERO_DOC"]))
        self.data1["NUMERO_DOC"] = self.data1["NIT PROVEEDOR FLETE"].map(map_num_doc)

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)

        c = 2
        t = 7

        for _, fila in self.enc_data1.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(451)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:0>1.0f}".format(0)
                + "{:0>1.0f}".format(1)
                + "{:3}".format(self.CO)
                + "{:3}".format(TIPO_DOCUMENTO)
                + "{:0>8.0f}".format(fila["NUMERO_DOC"])
                + "{:8}".format(self.fecha)
                + "{:<15}".format(fila["NIT PROVEEDOR FLETE"])
                + "{:3}".format("408")
                + "{:0>1.0f}".format(1)
                + "{:0>1.0f}".format(0)
                + "{:255}".format(".")
                + "{:3}".format("401")
                + "{:3}".format("403")
                + "{:3}".format("001")
                + "{:<15}".format(self.COMPRADOR)
                + "{:12}".format(fila["LOTE"])[:12]
                + "{:3}".format(MONEDA)
                + "{:3}".format(MONEDA)
                + "{:0>13.4f}".format(1)
                + "{:3}".format(MONEDA)
                + "{:0>13.4f}".format(1)
                + "{:0>8.4f}".format(0)
                + "{:0>8.4f}".format(0)
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
                + "{:0>1.0f}".format(0)
            )
            self.d0.append(row)
            c += 1

        for _, fila in self.data1.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(470)
                + "{:0>2.0f}".format(1)
                + "{:0>2.0f}".format(8)
                + "{:0>3.0f}".format(self.CIA)
                + "{:3}".format(self.CO)
                + "{:3}".format(TIPO_DOCUMENTO)
                + "{:0>8.0f}".format(fila["NUMERO_DOC"])
                + "{:0>10.0f}".format(1)
                + "{:55}".format(" ")
                + "{:5}".format(self.BODEGA)
                + "{:10}".format(" ")
                + "{:15}".format(" ")
                + "{:3}".format("401")
                + "{:2}".format(MOTIVO)
                + "{:0>1.0f}".format(0)
                + "{:3}".format(self.CO)
                + "{:2}".format(" ")
                + "{:15}".format(" ")
                + "{:15}".format(" ")
                + "{:3}".format(" ")
                + "{:<4}".format("U")
                + "{:<4}".format("U")
                + "{:0>20.4f}".format(1)
                + "{:0>20.4f}".format(0)
                + "{:0>20.4f}".format(fila["flete*animal"])
                + "{:0>1.0f}".format(1)
                + "{:0>1.0f}".format(0)
                + "{:0>1.0f}".format(0)
                + "{:255}".format(fila["LOTE"])
                + "{:2000}".format(" ")
                + "{:40}".format(" ")
                + "{:<4}".format("U")
                + "{:0>7.0f}".format(0)
                + "{:50}".format("99088")
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:<20}".format(self.UN)
            )
            self.d0.append(row)
            c += 1

        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir, empresa_id=None, fecha=None, parametros=None, datos=None):
    """Ejecuta el flujo de Flete Bovino y devuelve el resultado."""
    if not empresa_id:
        raise ValueError("Debes seleccionar la empresa.")
    if not fecha:
        raise ValueError("Debes indicar la fecha de sacrificio (AAAAMMDD).")

    proc = FleteBovino(excel_path, work_dir, empresa_id, fecha, parametros, datos)
    proc.dataframe()
    proc.consecutivo_documento()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "FacturaFletes.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.data1)
    return resultado

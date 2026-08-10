"""Procesador de Compromisos de Pedidos para Siesa (documento OPV).

Portado desde ``7.B_COMPROMISOS_PEDIDOS.py``. Genera los compromisos de entrega
de los pedidos (registros 405) a partir de la hoja CANAL de ANALISIS.xlsx y la
tabla de referencias FRIGOAPP -> SIESA. Conserva intacta la lógica de trama.
"""

import os

import pandas as pd

from . import siesa

USER = siesa.SIESA_USER
PASSWORD = siesa.SIESA_PASSWORD

TIPO_DOCUMENTO = "OPV"
# Valores fijos del ejecutable de compromisos de pedidos.
CO = "301"
BODEGA = "30101"


class CompromisosPedidos:
    def __init__(self, excel_path, work_dir, empresa_id, fecha, parametros=None, datos=None):
        self.excel_path = excel_path
        self.work_dir = work_dir
        self.fecha = fecha
        self.CO = CO
        self.BODEGA = BODEGA

        self.data1 = siesa.leer_datos_canal(
            datos, excel_path,
            dtype={"NIT": str, "FECHA SACRIFICIO SIESA": str, "FECHA PEDIDO SIESA": str,
                   "SUCURSAL": str, "NIT CLIENTE ": str},
            skiprows=6,
        )
        # La compañía se toma de la hoja CANAL (o del selector en modo manual).
        if parametros is not None:
            self.CIA = int(empresa_id)
        else:
            self.CIA = int(self.data1["CIA"].iloc[0])
            siesa.validar_empresa(self.CIA, empresa_id)
        self.CIA_CONEXION = str(int(self.CIA))

        self.referencias = pd.read_excel(
            siesa.ARCHIVO_REFERENCIAS, sheet_name="Hoja 2",
            dtype={"SIESA": str}, skiprows=1,
        )
        self.d0 = []

    def mapeo_referencias(self):
        mapeo = dict(zip(self.referencias["FRIGOAPP"], self.referencias["SIESA"]))
        self.data1["REF"] = self.data1["TIPO"].map(mapeo)

    def dataframe(self):
        self.data1 = self.data1[self.data1["NIT CLIENTE "].notna()]
        self.data1 = self.data1[self.data1["REMISION"].notna()]
        self.data1["NUMERO_DOC"] = 0
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]
        self.data1 = self.data1[self.data1["FECHA SACRIFICIO SIESA"] == str(self.fecha)]

    def dataframe2(self):
        self.data1["FRÍO(kg)"] = round(self.data1["FRÍO(kg)"], 2)
        self.data_compromisos = self.data1.copy()

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)

        c = 2
        t = 7

        for _, fila in self.data_compromisos.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(405)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(3)
                + "{:0>3.0f}".format(self.CIA)
                + "{:3}".format(self.CO)
                + "{:3}".format(TIPO_DOCUMENTO)
                + "{:0>8.0f}".format(fila["REMISION"])
                + "{:0>7.0f}".format(0)
                + "{:<50}".format(fila["REF"])
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:5}".format(self.BODEGA)
                + "{:10}".format(" ")
                + "{:<15}".format(fila["LOTE"])
                + "{:<4}".format("KG")
                + "{:0>20.4f}".format(fila["FRÍO(kg)"])
                + "{:0>20.4f}".format(0)
                + "{:0>10.0f}".format(c - 1)
            )
            self.d0.append(row)
            c += 1

        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir, empresa_id=None, fecha=None, parametros=None, datos=None):
    """Ejecuta el flujo de Compromisos de Pedidos y devuelve el resultado."""
    if not empresa_id:
        raise ValueError("Debes seleccionar la empresa.")
    if not fecha:
        raise ValueError("Debes indicar la fecha del pedido (AAAAMMDD).")

    proc = CompromisosPedidos(excel_path, work_dir, empresa_id, fecha, parametros, datos)
    proc.mapeo_referencias()
    proc.dataframe()
    proc.dataframe2()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "Compromiso_PedidoVentaCanal.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.data_compromisos)
    return resultado

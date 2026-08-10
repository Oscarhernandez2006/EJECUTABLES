"""Procesador de Impuestos de Sacrificio para Siesa (documento EAC).

Portado desde ``6._IMPUESTOS_SACRIFICIO.py``. Genera un documento por cada
impuesto (registros 451 y 470). Requiere dos archivos:
  - ANALISIS.xlsx (hoja CANAL) con las canales.
  - IMP_SACRIFICIO.xlsx (hoja Hoja1) con los impuestos: NIT, SUCURSAL,
    REFERENCIA y VALOR IMPUESTO, y una columna TIPO (1 bovino, 2 porcino).

Los impuestos aplicados se filtran por TIPO según el servicio de compra
(1690 = bovino). Conserva intacta la lógica de trama.
"""

import os

import pandas as pd

from . import siesa

USER = os.getenv("SIESA_IMPUESTOS_USER", "webservices")
PASSWORD = os.getenv("SIESA_IMPUESTOS_PASSWORD", "Santacruz2026*")

MOTIVO = "01"
TIPO_DOCUMENTO = "EAC"
MONEDA = "COP"
# Bodega y comprador fijos del proceso original de impuestos.
BODEGA = "00101"
UN = "001"
COMPRADOR = "3730782"


class ImpuestosSacrificio:
    def __init__(self, analisis_path, impuestos_path, work_dir, empresa_id, fecha, parametros=None):
        self.work_dir = work_dir
        self.fecha = fecha

        if parametros:
            self.CIA = int(empresa_id)
            self.CO = str(parametros["CO"])
            self.SERVICIO_COMPRA = int(parametros["SERVICIO_COMPRA"])
        else:
            # Parámetros de las hojas PARAMETROS y PARAMETROS ITEMS, igual que el ejecutable.
            self.data2 = pd.read_excel(
                analisis_path, sheet_name="PARAMETROS", dtype={"CO": str, "BODEGA": str, "UN": str})
            self.data3 = pd.read_excel(
                analisis_path, sheet_name="PARAMETROS ITEMS", dtype={"CODIGO_PARAMETRO": str})
            self.CIA = int(self.data2["CODIGO_PARAMETRO"].iloc[0])
            self.CO = str(int(self.data2["CODIGO_PARAMETRO"].iloc[1]))
            self.SERVICIO_COMPRA = int(self.data3["CODIGO_PARAMETRO"].iloc[0])
            siesa.validar_empresa(self.CIA, empresa_id)
        self.CIA_CONEXION = str(int(self.CIA))

        self.data1 = pd.read_excel(
            analisis_path, sheet_name="CANAL",
            dtype={"NIT": str, "FECHA SACRIFICIO SIESA": str},
            skiprows=6,
        )
        self.data4 = pd.read_excel(
            impuestos_path, sheet_name="Hoja1",
            dtype={"NIT": str, "SUCURSAL": str, "ITEMS": str, "REFERENCIA": str},
            skiprows=1,
        )

        # Se capturan los 6 impuestos por posición antes de filtrar.
        self.IMP_NIT = [self.data4["NIT"].iloc[k] for k in range(6)]
        self.IMP_SUC = [self.data4["SUCURSAL"].iloc[k] for k in range(6)]
        self.IMP_VR = [self.data4["VALOR IMPUESTO"].iloc[k] for k in range(6)]
        self.IMP_ITEM = [self.data4["REFERENCIA"].iloc[k] for k in range(6)]
        self.d0 = []

    def dataframe(self):
        self.data1["Fecha_control"] = ""
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]
        self.data1 = self.data1[self.data1["FECHA SACRIFICIO SIESA"] == self.fecha]
        if self.SERVICIO_COMPRA == 1690:
            self.data4 = self.data4[self.data4["TIPO"] == 1]
        else:
            self.data4 = self.data4[self.data4["TIPO"] == 2]

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)

        c = 2
        t = 7

        # Encabezado: un documento por impuesto (registro 451).
        for i, _ in self.data4.iterrows():
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
                + "{:0>8.0f}".format(i + 1)
                + "{:8}".format(self.fecha)
                + "{:<15}".format(self.IMP_NIT[i])[:15]
                + "{:3}".format("408")
                + "{:0>1.0f}".format(1)
                + "{:0>1.0f}".format(0)
                + "{:255}".format(".")
                + "{:3}".format("401")
                + "{:3}".format("403")
                + "{:3}".format(self.IMP_SUC[i])
                + "{:<15}".format(COMPRADOR)
                + "{:12}".format(" ")
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

        # Detalle: por cada impuesto, una línea por cada canal (registro 470).
        for i, _ in self.data4.iterrows():
            for j, fila in self.data1.iterrows():
                row = (
                    siesa.generar_cons(c, t)
                    + "{:0>4.0f}".format(470)
                    + "{:0>2.0f}".format(1)
                    + "{:0>2.0f}".format(8)
                    + "{:3}".format(self.CIA)
                    + "{:3}".format(self.CO)
                    + "{:3}".format(TIPO_DOCUMENTO)
                    + "{:0>8.0f}".format(i + 1)
                    + "{:0>10.0f}".format(j + 1)
                    + "{:55}".format(" ")
                    + "{:5}".format(BODEGA)
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
                    + "{:0>20.4f}".format(self.IMP_VR[i])
                    + "{:0>1.0f}".format(1)
                    + "{:0>1.0f}".format(0)
                    + "{:0>1.0f}".format(0)
                    + "{:255}".format(fila["LOTE"])
                    + "{:2000}".format(" ")
                    + "{:40}".format(" ")
                    + "{:<4}".format("U")
                    + "{:0>7.0f}".format(0)
                    + "{:<50}".format(self.IMP_ITEM[i])
                    + "{:20}".format(" ")
                    + "{:20}".format(" ")
                    + "{:20}".format(" ")
                    + "{:<20}".format(UN)
                )
                self.d0.append(row)
                c += 1

        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(entrada, work_dir, empresa_id=None, fecha=None, parametros=None):
    """Ejecuta el flujo de Impuestos de Sacrificio.

    ``entrada`` es un diccionario ``{'analisis': ruta, 'impuestos': ruta}``.
    """
    if not empresa_id:
        raise ValueError("Debes seleccionar la empresa.")
    if not fecha:
        raise ValueError("Debes indicar la fecha de sacrificio (AAAAMMDD).")

    analisis_path = entrada["analisis"]
    impuestos_path = entrada["impuestos"]

    proc = ImpuestosSacrificio(analisis_path, impuestos_path, work_dir, empresa_id, fecha, parametros)
    proc.dataframe()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "FacturaImpuestosBovinos.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.data1)
    return resultado

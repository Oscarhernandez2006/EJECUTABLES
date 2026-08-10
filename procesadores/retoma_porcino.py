"""Procesador de Retoma Porcino para Siesa (documento EIN).

Portado desde ``4.2B_RETOMA_PORCINO.py``. Genera la entrada de subproductos de
cerdo (víscera roja ref 2413, víscera blanca ref 2423 y cabeza ref 2002) en
bloques condicionados por la columna 'CONCEPTO'. Conserva intacta la trama.

NOTA: los costos (víscera roja/blanca y cabeza) y la bodega de subprocesos se
toman de la configuración por empresa y deben verificarse contra Siesa.
"""

import os

import pandas as pd

from . import siesa

USER = siesa.SIESA_USER
PASSWORD = siesa.SIESA_PASSWORD

MOTIVO = "02"
TIPO_DOCUMENTO = "EIN"
UN = "001"
TERCERO = "Generico"
CLASE_DOCUMENTO = 61
CONCEPTO = 601


class RetomaPorcino:
    def __init__(self, excel_path, work_dir, empresa_id, fecha, parametros=None, datos=None):
        self.excel_path = excel_path
        self.work_dir = work_dir
        self.fecha = fecha

        if parametros:
            self.CIA = int(empresa_id)
            self.CO = str(parametros["CO"])
            self.BODEGA_SUBPROCESOS = str(parametros["BODEGA_SUBPROCESOS"])
            self.COSTO_VISCERA_ROJA = float(parametros["COSTO_VISCERA_ROJA"])
            self.COSTO_VISCERA_BLANCA = float(parametros["COSTO_VISCERA_BLANCA"])
            self.COSTO_CABEZA_CERDO = float(parametros["COSTO_CABEZA_CERDO"])
        else:
            # Parámetros y costos de subproductos de la hoja PARAMETROS, igual que
            # el ejecutable (bodega subprocesos iloc[7], costos iloc[8]/[10]/[11]).
            self.data2 = pd.read_excel(
                excel_path, sheet_name="PARAMETROS", dtype={"CO": str, "BODEGA": str})
            self.CIA = self.data2["CODIGO_PARAMETRO"].iloc[0]
            self.CO = str(int(self.data2["CODIGO_PARAMETRO"].iloc[1]))
            self.BODEGA_SUBPROCESOS = str(int(self.data2["CODIGO_PARAMETRO"].iloc[7]))
            self.COSTO_VISCERA_ROJA = self.data2["CODIGO_PARAMETRO"].iloc[8]
            self.COSTO_VISCERA_BLANCA = self.data2["CODIGO_PARAMETRO"].iloc[10]
            self.COSTO_CABEZA_CERDO = self.data2["CODIGO_PARAMETRO"].iloc[11]
            siesa.validar_empresa(self.CIA, empresa_id)
        self.CIA_CONEXION = str(int(self.CIA))

        self.data1 = siesa.leer_datos_canal(
            datos, excel_path,
            dtype={"NIT PROVEEDOR": str, "FECHA SACRIFICIO SIESA": str, "LOTE": str},
            skiprows=6,
        )
        self.referencias = pd.read_excel(
            siesa.ARCHIVO_REFERENCIAS, sheet_name="Hoja 2",
            dtype={"SIESA": str}, skiprows=1,
        )
        self.d0 = []

    def mapeo_referencias(self):
        mapeo = dict(zip(self.referencias["FRIGOAPP"], self.referencias["SIESA"]))
        self.data1["REFERENCIA"] = self.data1["TIPO"].map(mapeo)

    def dataframe(self):
        self.data1["Fecha_control"] = ""
        self.data1["valor_total_piel"] = 0
        self.data1["NUMERO_DOC"] = 0
        for i, _ in self.data1.iterrows():
            self.data1.at[i, "NUMERO_DOC"] = i + 1
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]
        self.data1 = self.data1[self.data1["FECHA SACRIFICIO SIESA"] == self.fecha]
        self.data1 = self.data1[self.data1["PESO COMPRA"] > 0]
        self.data1["COSTO_UNITARIO"] = self.data1["total costo tat"] / self.data1["PEC(kg)"]
        for i, _ in self.data1.iterrows():
            self.data1.at[i, "COSTO_UNITARIO"] = round(self.data1.at[i, "COSTO_UNITARIO"], 2)

    def _detalle(self, c, ti, costo, referencia, nota="ENTRADA POR SARIFICIO"):
        return (
            siesa.generar_cons(c, 7)
            + "{:0>4.0f}".format(470)
            + "{:0>2.0f}".format(0)
            + "{:0>2.0f}".format(12)
            + "{:0>3.0f}".format(self.CIA)
            + "{:3}".format(self.CO)
            + "{:3}".format(TIPO_DOCUMENTO)
            + "{:0>8.0f}".format(1)
            + siesa.generar_cons(c, ti)
            + "{:55}".format(" ")
            + "{:5}".format(self.BODEGA_SUBPROCESOS)
            + "{:10}".format(" ")
            + "{:15}".format(" ")
            + "{:0>3.0f}".format(CONCEPTO)
            + "{:2}".format(MOTIVO)
            + "{:3}".format(self.CO)
            + "{:2}".format(" ")
            + "{:15}".format(" ")
            + "{:15}".format(" ")
            + "{:4}".format("U")
            + "{:0>20.4f}".format(1)
            + "{:0>20.4f}".format(0)
            + "{:0>20.4f}".format(costo)
            + "{:255}".format(nota)
            + "{:2000}".format(" ")
            + "{:40}".format(" ")
            + "{:4}".format("U")
            + "{:10}".format(" ")
            + "{:15}".format(" ")
            + "{:7}".format(0000000)
            + "{:<50}".format(referencia)
            + "{:20}".format(" ")
            + "{:20}".format(" ")
            + "{:20}".format(" ")
            + "{:20}".format(UN)
            + "{:0>10.0f}".format(0)
        )

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)

        c = 2
        t = 7
        ti = 10

        # Encabezado (registro 450).
        row = (
            siesa.generar_cons(c, t)
            + "{:0>4.0f}".format(450)
            + "{:0>2.0f}".format(0)
            + "{:0>2.0f}".format(2)
            + "{:0>3.0f}".format(self.CIA)
            + "{:0>1.0f}".format(1)
            + "{:3}".format(self.CO)
            + "{:3}".format(TIPO_DOCUMENTO)
            + "{:0>8.0f}".format(1)
            + "{:8}".format(self.fecha)
            + "{:15}".format(TERCERO)
            + "{:0>3.0f}".format(CLASE_DOCUMENTO)
            + "{:0>1.0f}".format(0)
            + "{:0>1.0f}".format(0)
            + "{:255}".format(" ")
            + "{:0>3.0f}".format(CONCEPTO)
            + "{:5}".format(" ")
            + "{:5}".format(" ")
            + "{:15}".format(" ")
            + "{:3}".format(" ")
            + "{:3}".format(" ")
            + "{:0>8.0f}".format(0)
            + "{:10}".format(" ")
            + "{:15}".format(" ")
            + "{:3}".format(" ")
            + "{:15}".format(" ")
            + "{:50}".format(" ")
            + "{:15}".format(" ")
            + "{:0>30.0f}".format(0)
            + "{:0>15.0f}".format(0)
            + "{:0>20.0f}".format(0)
            + "{:0>20.0f}".format(0)
            + "{:0>20.0f}".format(0)
            + "{:255}".format(" ")
        )
        self.d0.append(row)
        c += 1

        # Bloque víscera roja (ref 2413), solo CERDO EN PIE.
        for i, _ in self.data1.iterrows():
            if self.data1.at[i, "CONCEPTO"] == "CERDO EN PIE":
                self.d0.append(self._detalle(c, ti, self.COSTO_VISCERA_ROJA, "2413"))
                c += 1

        # Bloque víscera blanca (ref 2423), solo CERDO EN PIE.
        for i, _ in self.data1.iterrows():
            if self.data1.at[i, "CONCEPTO"] == "CERDO EN PIE":
                self.d0.append(self._detalle(c, ti, self.COSTO_VISCERA_BLANCA, "2423", "ENTRADA POR SARIFICIO PORCINO"))
                c += 1

        # Bloque cabeza (ref 2002), CERDO EN PIE o canales con cabeza.
        for i, _ in self.data1.iterrows():
            concepto = self.data1.at[i, "CONCEPTO"]
            if concepto in ("CERDO EN PIE", "CANAL CALIENTE CON CABEZA", "CANAL FRIA CON CABEZA"):
                self.d0.append(self._detalle(c, ti, self.COSTO_CABEZA_CERDO, "2002"))
                c += 1

        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir, empresa_id=None, fecha=None, parametros=None, datos=None):
    """Ejecuta el flujo de Retoma Porcino y devuelve el resultado."""
    if not empresa_id:
        raise ValueError("Debes seleccionar la empresa.")
    if not fecha:
        raise ValueError("Debes indicar la fecha de sacrificio (AAAAMMDD).")

    proc = RetomaPorcino(excel_path, work_dir, empresa_id, fecha, parametros, datos)
    proc.mapeo_referencias()
    proc.dataframe()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "Entrada_canal.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.data1)
    return resultado

"""Procesador de Cargue de Lotes para Siesa (documento EII, registros 403).

Portado desde ``4.1_CARGUE_LOTES.py``. Crea los lotes de producción necesarios
para la posterior entrada de canales. Conserva intacta la lógica de trama.

La referencia de cada lote se obtiene mapeando la columna 'TIPO' de la hoja CANAL
contra la tabla FRIGOAPP -> SIESA del archivo de referencias empaquetado.
"""

import os

import pandas as pd

from . import siesa

USER = siesa.SIESA_USER
PASSWORD = siesa.SIESA_PASSWORD

INDICADOR_ACTUALIZACION = 1


class CargueLotes:
    def __init__(self, excel_path, work_dir, empresa_id, fecha, parametros=None, datos=None):
        self.excel_path = excel_path
        self.work_dir = work_dir
        self.fecha = fecha

        if parametros is not None:
            # Solo requiere la compañía, que viene del selector de empresa.
            self.CIA = int(empresa_id)
        else:
            # CIA de la hoja PARAMETROS, igual que el ejecutable.
            self.data2 = pd.read_excel(
                excel_path, sheet_name="PARAMETROS", dtype={"CO": str, "BODEGA": str})
            self.CIA = self.data2["CODIGO_PARAMETRO"].iloc[0]
            siesa.validar_empresa(self.CIA, empresa_id)
        self.CIA_CONEXION = str(int(self.CIA))

        self.data1 = siesa.leer_datos_canal(
            datos, excel_path,
            dtype={"NIT": str, "FECHA SACRIFICIO SIESA": str, "LOTE": str},
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
        self.data1["NUMERO_DOC"] = 0
        for i, _ in self.data1.iterrows():
            self.data1.at[i, "NUMERO_DOC"] = i + 1
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]
        self.data1 = self.data1[self.data1["FECHA SACRIFICIO SIESA"] == self.fecha]

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)

        c = 2
        t = 7

        for _, fila in self.data1.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(403)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:0>1.0f}".format(INDICADOR_ACTUALIZACION)
                + "{:<15}".format(fila["LOTE"])
                + "{:0>7.0f}".format(0)
                + "{:50}".format(fila["REFERENCIA"])
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:3}".format(" ")
                + "{:0>1.0f}".format(1)
                + "{:8}".format(self.fecha)
                + "{:8}".format("20301231")
                + "{:15}".format(" ")
                + "{:15}".format(" ")
                + "{:3}".format(" ")
                + "{:40}".format(" ")
                + "{:15}".format(" ")
                + "{:8}".format(" ")
                + "{:255}".format("Lote unico")
            )
            self.d0.append(row)
            c += 1

        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir, empresa_id=None, fecha=None, parametros=None, datos=None):
    """Ejecuta el flujo de Cargue de Lotes y devuelve el resultado."""
    if not empresa_id:
        raise ValueError("Debes seleccionar la empresa.")
    if not fecha:
        raise ValueError("Debes indicar la fecha de sacrificio (AAAAMMDD).")

    proc = CargueLotes(excel_path, work_dir, empresa_id, fecha, parametros, datos)
    proc.mapeo_referencias()
    proc.dataframe()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "Creacion_lotes.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.data1)
    return resultado

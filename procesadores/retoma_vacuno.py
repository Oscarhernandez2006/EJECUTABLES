"""Procesador de Retoma Vacuno para Siesa (documento EIN).

Portado desde ``4.2A_RETOMA_VACUNO.py``. Genera la entrada de subproductos
(piel, sebo, retomas y vísceras) tras el sacrificio, en cuatro bloques de
detalle (registros 470 v12) bajo un mismo encabezado (450).

NOTA: el script de escritorio usaba una variable ``BODEGA_PROCESO`` que no está
definida en ninguno de los archivos originales (fallaría tal cual). Aquí se usa
la bodega de subproductos de la empresa (``BODEGA_SUBPRODUCTO`` en la config),
que es el destino lógico de estos movimientos. Verificar el valor por empresa.
"""

import os

import pandas as pd

from . import siesa

USER = os.getenv("SIESA_RETOMA_USER", "webservices")
PASSWORD = os.getenv("SIESA_RETOMA_PASSWORD", "Santacruz2026*")

MOTIVO = "02"
TIPO_DOCUMENTO = "EIN"
UN = "001"
TERCERO = "Generico"
CLASE_DOCUMENTO = 61
CONCEPTO = 601


class RetomaVacuno:
    def __init__(self, excel_path, work_dir, empresa_id, fecha, parametros=None):
        self.excel_path = excel_path
        self.work_dir = work_dir
        self.fecha = fecha

        if parametros:
            self.CIA = int(empresa_id)
            self.CO = str(parametros["CO"])
            self.BODEGA_PROCESO = str(parametros["BODEGA_PROCESO"])
        else:
            # CIA/CO de PARAMETROS. El ejecutable original tenía un bug
            # (BODEGA_PROCESO no definida): aquí se toma la bodega de subproductos
            # de la propia hoja PARAMETROS (búsqueda por nombre) con respaldo a BODEGA.
            self.data2 = pd.read_excel(
                excel_path, sheet_name="PARAMETROS", dtype={"CO": str, "BODEGA": str})
            self.CIA = self.data2["CODIGO_PARAMETRO"].iloc[0]
            self.CO = str(int(self.data2["CODIGO_PARAMETRO"].iloc[1]))
            subproducto = siesa.param_por_nombre(self.data2, "SUBPRODUCTO")
            if subproducto is None:
                subproducto = self.data2["CODIGO_PARAMETRO"].iloc[2]
            self.BODEGA_PROCESO = str(int(subproducto))
            siesa.validar_empresa(self.CIA, empresa_id)
        self.CIA_CONEXION = str(int(self.CIA))

        self.data1 = pd.read_excel(
            excel_path, sheet_name="CANAL",
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
        self.map_precios_KG_piel = self.referencias["SIESA_SEBO"].iloc[10]
        self.map_precios_KG_sebo = self.referencias["SIESA_SEBO"].iloc[11]
        self.data1 = self.data1[self.data1["NIT PROVEEDOR"].notna()]
        self.data1["NUMERO_DOC"] = 0
        for i, _ in self.data1.iterrows():
            self.data1.at[i, "NUMERO_DOC"] = i + 1
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]
        self.data1 = self.data1[self.data1["FECHA SACRIFICIO SIESA"] == self.fecha]
        self.data1 = self.data1[self.data1["PESO EN FINCA"] > 0]
        self.data1["VR_BRUTO"] = (self.data1["P.NETO"] * self.data1["P.PROM FINCA"]).round(2)
        self.data1["valor_total_piel"] = self.map_precios_KG_piel * self.data1["K. piel"]
        self.data1["valor_total_sebo"] = self.map_precios_KG_sebo * self.data1["k. sebo"]
        self.data1["COSTO_UNITARIO"] = self.data1["total costo tat"] / self.data1["PEC(kg)"]
        for i, _ in self.data1.iterrows():
            self.data1.at[i, "COSTO_UNITARIO"] = round(self.data1.at[i, "COSTO_UNITARIO"], 2)
        for i, _ in self.data1.iterrows():
            self.data1.at[i, "COSTO_PIEL"] = self.data1.at[i, "valor piel "] / self.data1.at[i, "PIEL(kg)"]
        self.data1["COSTO_PIEL"] = round(self.data1["COSTO_PIEL"], 2)
        self.data1["LOTE"] = self.data1["LOTE.1"]

    def _detalle(self, c, ti, bodega, um, cantidad, costo, referencia):
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
            + "{:5}".format(bodega)
            + "{:10}".format(" ")
            + "{:15}".format(" ")
            + "{:0>3.0f}".format(CONCEPTO)
            + "{:2}".format(MOTIVO)
            + "{:3}".format(self.CO)
            + "{:2}".format(" ")
            + "{:15}".format(" ")
            + "{:15}".format(" ")
            + "{:4}".format(um)
            + "{:0>20.4f}".format(cantidad)
            + "{:0>20.4f}".format(0)
            + "{:0>20.4f}".format(costo)
            + "{:255}".format("ENTRADA POR SARIFICIO")
            + "{:2000}".format(" ")
            + "{:40}".format(" ")
            + "{:4}".format(um if um == "U" else " ")
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

        # Bloque piel (ref 3238).
        for _, fila in self.data1.iterrows():
            self.d0.append(self._detalle(c, ti, self.BODEGA_PROCESO, "KG", fila["K. piel"], fila["COSTO_PIEL"], "3238"))
            c += 1

        # Bloque sebo (ref 3249).
        for _, fila in self.data1.iterrows():
            costo_sebo = int(fila["valor sebo"] / fila["k. sebo"])
            self.d0.append(self._detalle(c, ti, self.BODEGA_PROCESO, "KG", fila["k. sebo"], costo_sebo, "3249"))
            c += 1

        # Bloque retomas (ref 3260, unidad U, cantidad 1).
        for _, fila in self.data1.iterrows():
            self.d0.append(self._detalle(c, ti, self.BODEGA_PROCESO, "U", 1, fila["retomas"], "3260"))
            c += 1

        # Bloque vísceras (ref 1618, unidad U, cantidad 1).
        for _, fila in self.data1.iterrows():
            self.d0.append(self._detalle(c, ti, self.BODEGA_PROCESO, "U", 1, fila["v.visceras unidad"], "1618"))
            c += 1

        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir, empresa_id=None, fecha=None, parametros=None):
    """Ejecuta el flujo de Retoma Vacuno y devuelve el resultado."""
    if not empresa_id:
        raise ValueError("Debes seleccionar la empresa.")
    if not fecha:
        raise ValueError("Debes indicar la fecha de sacrificio (AAAAMMDD).")

    proc = RetomaVacuno(excel_path, work_dir, empresa_id, fecha, parametros)
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

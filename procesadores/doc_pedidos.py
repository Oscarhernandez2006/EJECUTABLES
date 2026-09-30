"""Procesador de Documentos de Pedidos para Siesa (documento OPV).

Portado desde ``7.A_DOC_PEDIDOS.py``. Genera el pedido de venta de canales
(registros 430 y 431) a partir de la hoja CANAL de ANALISIS.xlsx y la tabla de
referencias FRIGOAPP -> SIESA. Conserva intacta la lógica de trama.
"""

import os

import pandas as pd

from . import siesa

USER = siesa.SIESA_USER
PASSWORD = siesa.SIESA_PASSWORD

CONDICION_PAGO = "02D"
TIPO_CLIENTE = "001"
MOTIVO = "01"
TIPO_DOCUMENTO = "OPV"
LISTA_PRECIOS = "999"
PUNTO_ENVIO = "000"
# Valores fijos del ejecutable de documentos de pedidos.
CO = "301"
BODEGA = "30101"
UN = "003"
# Debe coincidir con compromisos_pedidos para que lo comprometido cuadre con lo pedido.
DECIMALES_KG = 2


class DocPedidos:
    def __init__(self, excel_path, work_dir, empresa_id, fecha, parametros=None, datos=None):
        self.excel_path = excel_path
        self.work_dir = work_dir
        self.fecha = fecha
        self.CO = CO
        self.BODEGA = BODEGA
        self.UN = UN

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
        self.data1 = siesa.filtrar_pedidos(self.data1, self.fecha)
        siesa.exigir_referencias(self.data1, col_codigo="TIPO", col_ref="REF",
                                 origen="el archivo CODIGO SIESA.xlsx")
        siesa.exigir_columna_positiva(self.data1, "FRÍO(kg)", "Peso FRÍO(kg)")
        siesa.exigir_columna_positiva(self.data1, "P.VENTA", "Precio de venta (P.VENTA)")
        self.data1["NUMERO_DOC"] = 0
        self.data1["LOTE"] = self.data1["LOTE"].astype(str).str[:15]

    def dataframe2(self):
        self.data1["FRÍO(kg)"] = pd.to_numeric(self.data1["FRÍO(kg)"]).round(DECIMALES_KG)
        self.data_enc = self.data1.copy()
        self.data_mov = self.data1.copy()
        self.data_enc.drop_duplicates(subset="REMISION", inplace=True)
        self.data_mov = self.data_mov.groupby(["REMISION", "REF"], as_index=False).agg(
            CANTIDAD=("FRÍO(kg)", "sum"),
            NIT_CLIENTE=("NIT CLIENTE ", "first"),
            FECHA=("FECHA SACRIFICIO SIESA", "first"),
            PRECIO=("P.VENTA", "first"),
        )

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)

        c = 2
        t = 7
        ci = 1
        ti = 10
        encabezados = {}
        detalles = {}

        # Encabezado del pedido (registro 430).
        for _, fila in self.data_enc.iterrows():
            row = (
                siesa.generar_cons(c, 7)
                + "{:0>4.0f}".format(430)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:0>1.0f}".format(1)
                + "{:0>1.0f}".format(1)
                + "{:0>1.0f}".format(1)
                + "{:3}".format(self.CO)
                + "{:3}".format(TIPO_DOCUMENTO)
                + "{:0>8.0f}".format(fila["REMISION"])
                + "{:8}".format(self.fecha)
                + "{:0>3.0f}".format(502)
                + "{:0>1.0f}".format(2)
                + "{:0>1.0f}".format(0)
                + "{:<15}".format(fila["NIT CLIENTE "])
                + "{:3}".format(fila["SUCURSAL"])
                + "{:<15}".format(fila["NIT CLIENTE "])
                + "{:3}".format(fila["SUCURSAL"])
                + "{:4}".format(TIPO_CLIENTE)
                + "{:3}".format(self.CO)
                + "{:8}".format(fila["FECHA SACRIFICIO SIESA"])
                + "{:0>3.0f}".format(3)
                + "{:15}".format(fila["REMISION"])
                + "{:10}".format(fila["REMISION"])
                + "{:10}".format(" ")
                + "{:3}".format("COP")
                + "{:3}".format("COP")
                + "{:0>13.4f}".format(1)
                + "{:3}".format("COP")
                + "{:0>13.4f}".format(1)
                + "{:3}".format(CONDICION_PAGO)
                + "{:0>1.0f}".format(0)
                + "{:2000}".format("Sitio de entrega")
                + "{:15}".format(" ")
                + "{:3}".format(PUNTO_ENVIO)
                + "{:15}".format(" ")
                + "{:50}".format(".")
                + "{:40}".format("Sitio de entrega")
                + "{:40}".format(" ")
                + "{:40}".format(" ")
                + "{:3}".format("169")
                + "{:2}".format("11")
                + "{:3}".format("001")
                + "{:40}".format(" ")
                + "{:20}".format("5460000")
                + "{:20}".format(" ")
                + "{:10}".format(" ")
                + "{:50}".format(".")
                + "{:0>1.0f}".format(0)
            )
            encabezados[fila["REMISION"]] = row
            c += 1

        # Detalle del pedido (registro 431).
        for _, fila in self.data_mov.iterrows():
            row = (
                siesa.generar_cons(c, t)
                + "{:0>4.0f}".format(431)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:3}".format(self.CO)
                + "{:3}".format(TIPO_DOCUMENTO)
                + "{:0>8.0f}".format(fila["REMISION"])
                + siesa.generar_cons(ci, ti)
                + "{:0>7.0f}".format(0)
                + "{:<50}".format(fila["REF"])
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:5}".format(self.BODEGA)
                + "{:0>3.0f}".format(501)
                + "{:2}".format(MOTIVO)
                + "{:0>1.0f}".format(0)
                + "{:3}".format(self.CO)
                + "{:20}".format(self.UN)
                + "{:<15}".format(" ")
                + "{:15}".format(" ")
                + "{:8}".format(fila["FECHA"])
                + "{:0>3.0F}".format(2)
                + "{:3}".format(LISTA_PRECIOS)
                + "{:<4}".format("kg")
                + "{:0>20.4f}".format(fila["CANTIDAD"])
                + "{:0>20.4f}".format(0)
                + "{:0>20.4f}".format(fila["PRECIO"])
                + "{:0>1.0f}".format(0)
                + "{:255}".format(".")
                + "{:2000}".format(" ")
                + "{:0>1.0f}".format(5)
                + "{:0>1.0f}".format(2)
            )
            detalles.setdefault(fila["REMISION"], []).append(row)
            ci += 1
            c += 1

        # Un bloque por pedido (encabezado + su detalle) para enviarlo por lotes.
        self.bloques = [[enc] + detalles.get(rem, []) for rem, enc in encabezados.items()]
        for bloque in self.bloques:
            self.d0.extend(bloque)

        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir, empresa_id=None, fecha=None, parametros=None, datos=None):
    """Ejecuta el flujo de Documentos de Pedidos y devuelve el resultado."""
    if not empresa_id:
        raise ValueError("Debes seleccionar la empresa.")
    if not fecha:
        raise ValueError("Debes indicar la fecha del pedido (AAAAMMDD).")

    proc = DocPedidos(excel_path, work_dir, empresa_id, fecha, parametros, datos)
    siesa.reportar_progreso(10, "Leyendo y validando el archivo…")
    proc.mapeo_referencias()
    proc.dataframe()
    proc.dataframe2()
    proc.generar_trama()

    siesa.guardar_trama(proc.d0, os.path.join(work_dir, "PedidoVentaCanal.txt"))
    resultado = siesa.enviar_por_lotes(proc.bloques, proc.CIA, proc.CIA_CONEXION, work_dir, USER, PASSWORD)

    resultado["registros"] = len(proc.data_mov)
    return resultado

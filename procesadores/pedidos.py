"""Procesador de Pedidos para Siesa.

Lee la hoja 'PEDIDO' del Excel cargado, genera la trama de importación de
pedidos (tipos de registro 430/431) y la envía al servicio web de Siesa.
"""

import os

import pandas as pd

from . import siesa

# Credenciales del servicio web (configurables por variables de entorno).
USER = os.getenv("SIESA_PEDIDOS_USER", "webservices")
PASSWORD = os.getenv("SIESA_PEDIDOS_PASSWORD", "Santacruz2026*")


class Ped:
    def __init__(self, excel_path, work_dir):
        self.excel_path = excel_path
        self.work_dir = work_dir

        self.Ped = pd.read_excel(
            excel_path,
            sheet_name="PEDIDO",
            dtype={"N.I.T / C.C.": str, "CODIGO": str, "BOD ENTRADA": str,
                   "BOD SALIDA": str, "SUCURSAL": str},
            skiprows=2,
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

        self.MOTIVO = "01"
        self.TIPO_DOC = "1PV"
        self.TIPO_CLIENTE = "001"
        self.CLASE_DOCUMENTO = "502"
        self.PUNTO_ENVIO = "000"

        self.CIA_CONEXION = str(int(self.CIA))

    def _ruta(self, nombre):
        return os.path.join(self.work_dir, nombre)

    def crear_dataframes(self):
        self.CIA = int(self.CIA)
        self.Ped["Número de documento"] = self.Ped.index + 1
        map_ref_siesa = dict(zip(self.EQUIVALENCIA["CODIGO"], self.EQUIVALENCIA["REF_SIESA"]))
        self.Ped["REF_SIESA"] = self.Ped["CODIGO"].map(map_ref_siesa)
        self.Ped2 = self.Ped.copy()
        self.Ped.drop_duplicates(["N.I.T / C.C."], keep="first", inplace=True)

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + str("{:0>3.0f}".format(self.CIA))
        self.d0.append(self.trama)
        c = 2
        for indice, fila in self.Ped.iterrows():
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
                + "{:3}".format(self.TIPO_DOC)
                + "{:0>8.0f}".format(fila["NUM_DOC"])
                + "{:8}".format(self.FECHA)
                + "{:0>3.0f}".format(502)
                + "{:0>1.0f}".format(0)
                + "{:0>1.0f}".format(0)
                + "{:15}".format(fila["N.I.T / C.C."])[:15]
                + "{:3}".format(fila["SUCURSAL"])[:3]
                + "{:15}".format(fila["N.I.T / C.C."])[:15]
                + "{:3}".format(fila["SUCURSAL"])[:3]
                + "{:4}".format(self.TIPO_CLIENTE)
                + "{:3}".format(self.CO)
                + "{:8}".format(self.FECHA)
                + "{:0>3.0f}".format(3)
                + "{:<15}".format(1)
                + "{:<10}".format(1)
                + "{:10}".format(" ")
                + "{:3}".format("COP")
                + "{:3}".format("COP")
                + "{:0>13.4f}".format(1)
                + "{:3}".format("COP")
                + "{:0>13.4f}".format(1)
                + "{:3}".format(fila["CON_PAGO"])
                + "{:0>1.0f}".format(0)
                + "{:2000}".format("VENTAS")
                + "{:15}".format(" ")
                + "{:3}".format(self.PUNTO_ENVIO)
                + "{:15}".format(self.VENDEDOR)
                + "{:50}".format(".")
                + "{:40}".format("Sitio de entrega")
                + "{:40}".format(" ")
                + "{:40}".format(" ")
                + "{:3}".format("169")
                + "{:2}".format("08")
                + "{:3}".format("001")
                + "{:40}".format(" ")
                + "{:20}".format("5460000")
                + "{:20}".format(" ")
                + "{:10}".format(" ")
                + "{:50}".format("facturacionelectronica@o.co")
                + "{:0>1.0f}".format(0)
            )
            self.d0.append(row)
            c = c + 1
        ci = 1
        ti = 10
        for indice, fila in self.Ped2.iterrows():
            row = (
                siesa.generar_cons(c, 7)
                + "{:0>4.0f}".format(431)
                + "{:0>2.0f}".format(0)
                + "{:0>2.0f}".format(2)
                + "{:0>3.0f}".format(self.CIA)
                + "{:3}".format(self.CO)
                + "{:3}".format(self.TIPO_DOC)
                + "{:0>8.0f}".format(fila["NUM_DOC"])
                + siesa.generar_cons(ci, ti)
                + "{:0>7.0f}".format(0)
                + "{:<50}".format(fila["REF_SIESA"])
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:20}".format(" ")
                + "{:5}".format(fila["BOD SALIDA"])
                + "{:0>3.0f}".format(501)
                + "{:2}".format(self.MOTIVO)
                + "{:0>1.0f}".format(0)
                + "{:3}".format(self.CO)
                + "{:20}".format(self.UN)
                + "{:<15}".format(" ")
                + "{:15}".format(" ")
                + "{:8}".format(self.FECHA)
                + "{:0>3.0F}".format(0)
                + "{:3}".format(self.LISTA_PRECIO)
                + "{:<4}".format("KG")
                + "{:0>20.4f}".format(fila["CANT.(kg)"])
                + "{:0>20.4f}".format(0)
                + "{:0>20.4f}".format(0)
                + "{:0>1.0f}".format(0)
                + "{:255}".format(" ")
                + "{:2000}".format(" ")
                + "{:0>1.0f}".format(5)
                + "{:0>1.0f}".format(1)
            )
            self.d0.append(row)
            c = c + 1
            ci = ci + 1
        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + str("{:0>3.0f}".format(self.CIA))
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir):
    """Ejecuta el flujo completo de Pedidos y devuelve el resultado."""
    proc = Ped(excel_path, work_dir)
    proc.crear_dataframes()
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "Ped_p.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.Ped2)
    return resultado

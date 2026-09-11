"""Procesador de Lista de Precios para Siesa.

Lee la hoja 'PDV' del Excel cargado, genera la trama de importación de la
lista de precios (tipo de registro 126) y la envía al servicio web de Siesa.
"""

import os

import pandas as pd

from . import siesa

# Credenciales del servicio web (configurables por variables de entorno).
USER = os.getenv("SIESA_PRECIOS_USER", siesa.SIESA_USER)
PASSWORD = os.getenv("SIESA_PRECIOS_PASSWORD", siesa.SIESA_PASSWORD)

# Fecha de inactivación por defecto (la de activación la fija el usuario).
FECHA_INACTIVACION = "20301231"


class Precios:
    def __init__(self, excel_path, work_dir, empresa_id=None, fecha=None):
        self.excel_path = excel_path
        self.work_dir = work_dir
        self.fecha = siesa.norm_fecha(fecha) if fecha else "20251224"

        self.precios = siesa.leer_hoja(
            excel_path,
            "PDV",
            dtype={"Cod_Lista": str, "Referencia": str, "U.M.": str},
        )

        # Solo filas con unidad de medida y precio: evita tramas inválidas.
        self.precios = self.precios[self.precios["U.M."].notna()]
        self.precios = self.precios[self.precios["Precio unit."].notna()]
        siesa.exigir_datos(
            self.precios,
            "La hoja PDV no tiene filas con U.M. y Precio unit. para procesar.",
        )

        # La compañía la fija el selector de empresa; el Excel actúa de salvaguarda.
        cia_excel = self.precios["Empresa"].iloc[0]
        siesa.validar_empresa(cia_excel, empresa_id)
        self.CIA = int(empresa_id) if empresa_id else int(cia_excel)
        self.CIA_CONEXION = str(self.CIA)

        self.d0 = []

    def generar_trama(self):
        reg_ini = 1
        self.trama = siesa.generar_consecutivo(reg_ini) + "00000001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama)
        c = 2
        for _, fila in self.precios.iterrows():
            row = (
                siesa.generar_cons(c, 7)                        # Número de registro
                + "{:0>4.0f}".format(126)                        # Tipo de registro
                + "{:0>2.0f}".format(0)                          # Subtipo de registro
                + "{:0>2.0f}".format(2)                          # Versión del tipo de registro
                + "{:0>3.0f}".format(self.CIA)                   # Compañía
                + "{:0>1.0f}".format(1)                          # Reemplaza item existente
                + "{:3}".format(fila["Cod_Lista"])               # Código de lista de precios
                + "{:0>7.0f}".format(0)                          # Código item
                + "{:50}".format(fila["Referencia"])             # Referencia item
                + "{:20}".format(" ")                            # Código de barras
                + "{:20}".format(" ")                            # Extensión 1
                + "{:20}".format(" ")                            # Extensión 2
                + "{:8}".format(self.fecha)                      # Fecha de activación
                + "{:8}".format(FECHA_INACTIVACION)              # Fecha de inactivación
                + "{:8}".format(0)                               # Código de promoción
                + "{:<4}".format(fila["U.M."])                   # Unidad de medida
                + "{:0>20.4f}".format(fila["Precio unit."])      # Precio
                + "{:0>20.4f}".format(0)                         # Precio mínimo
                + "{:0>20.4f}".format(0)                         # Precio máximo
                + "{:0>20.4f}".format(0)                         # Precio sugerido
            )
            self.d0.append(row)
            c = c + 1
        self.trama_final = siesa.generar_consecutivo(c) + "99990001" + "{:0>3.0f}".format(self.CIA)
        self.d0.append(self.trama_final)


def procesar(excel_path, work_dir, empresa_id=None, fecha=None):
    """Ejecuta el flujo completo de Lista de Precios y devuelve el resultado."""
    proc = Precios(excel_path, work_dir, empresa_id, fecha)
    proc.generar_trama()

    txt_path = os.path.join(work_dir, "Precios.txt")
    xml_path = os.path.join(work_dir, "doc.xml")

    siesa.guardar_trama(proc.d0, txt_path)
    siesa.generar_xml(txt_path, xml_path, proc.CIA_CONEXION, USER, PASSWORD)
    resultado = siesa.consumir_servicio_web(xml_path)

    resultado["registros"] = len(proc.precios)
    return resultado

"""Configuración de los ejecutables: catálogo de empresas.

Los parámetros de cada proceso ya no viven aquí: cada procesador los lee de la
hoja PARAMETROS del Excel, exactamente como los ejecutables originales. El
selector de empresa se valida contra la compañía (CIA) que trae el archivo.
"""

from .empresas import EMPRESAS, EMPRESA_IDS, empresa_valida, obtener_empresa
from .esquemas import (
    PARAMETROS_ESQUEMA,
    CANAL_COLUMNAS,
    DATOS_USADAS,
    HOJAS_MANUALES,
    esquema_de,
    columnas_usadas_de,
    datos_esquema_de,
    hojas_manuales_de,
    admite_parametros_manuales,
)

__all__ = [
    "EMPRESAS",
    "EMPRESA_IDS",
    "empresa_valida",
    "obtener_empresa",
    "PARAMETROS_ESQUEMA",
    "CANAL_COLUMNAS",
    "DATOS_USADAS",
    "HOJAS_MANUALES",
    "esquema_de",
    "columnas_usadas_de",
    "datos_esquema_de",
    "hojas_manuales_de",
    "admite_parametros_manuales",
]

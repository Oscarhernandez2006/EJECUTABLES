"""Configuración de empresas para los ejecutables de integración con Siesa.

Las empresas coinciden con las de SIGCOM (COMERCIALWEB). El ``id`` es el
código de compañía (CIA) en Siesa, que es el parámetro que diferencia el
comportamiento de cada proceso entre una empresa y otra.
"""

# Empresas disponibles. El id corresponde al código de compañía (CIA) en Siesa.
EMPRESAS = [
    {"id": "3", "nombre": "AGROPECUARIA SANTACRUZ", "corto": "Agropecuaria"},
    {"id": "8", "nombre": "CARNES FRIAS SANTACRUZ", "corto": "Carnes Frías"},
    {"id": "4", "nombre": "CARNES SANTACRUZ", "corto": "Carnes Santacruz"},
]

EMPRESA_IDS = [e["id"] for e in EMPRESAS]


def empresa_valida(empresa_id):
    """Indica si el id de empresa recibido es uno de los soportados."""
    return empresa_id in EMPRESA_IDS


def obtener_empresa(empresa_id):
    """Devuelve el diccionario de la empresa o ``None`` si no existe."""
    return next((e for e in EMPRESAS if e["id"] == empresa_id), None)

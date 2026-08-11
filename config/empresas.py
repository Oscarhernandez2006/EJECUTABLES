"""Configuración de empresas para los ejecutables de integración con Siesa.

Las empresas coinciden con las de SIGCOM (COMERCIALWEB). El ``id`` es el
código de compañía (CIA) en Siesa, que es el parámetro que diferencia el
comportamiento de cada proceso entre una empresa y otra.
"""

# Empresas disponibles. El id corresponde al código de compañía (CIA) en Siesa.
# ``logo`` es el archivo en static/img: Agropecuaria usa el suyo; las demás
# comparten el logo de Carnes Santacruz.
EMPRESAS = [
    {"id": "3", "nombre": "AGROPECUARIA SANTACRUZ", "corto": "Agropecuaria", "logo": "empresa-3.png"},
    {"id": "4", "nombre": "CARNES SANTACRUZ", "corto": "Carnes Santacruz", "logo": "empresa-4.png"},
    {"id": "6", "nombre": "CRISTIAN SERRANO", "corto": "Cristian Serrano", "logo": "empresa-4.png"},
    {"id": "7", "nombre": "INVERSIONES SERUEDA S.A.S", "corto": "Inversiones Serueda", "logo": "empresa-4.png"},
]

EMPRESA_IDS = [e["id"] for e in EMPRESAS]


def empresa_valida(empresa_id):
    """Indica si el id de empresa recibido es uno de los soportados."""
    return empresa_id in EMPRESA_IDS


def obtener_empresa(empresa_id):
    """Devuelve el diccionario de la empresa o ``None`` si no existe."""
    return next((e for e in EMPRESAS if e["id"] == empresa_id), None)

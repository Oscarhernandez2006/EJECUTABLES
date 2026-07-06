"""Paquete de procesadores para la integración con Siesa (Carnes Santa Cruz).

Cada módulo expone una función `procesar(excel_path, work_dir)` que:
  1. Lee el archivo Excel cargado por el usuario.
  2. Genera la trama de texto de posición fija.
  3. Convierte la trama a XML.
  4. Consume el servicio web SOAP de Siesa.

Y devuelve un diccionario con el resultado de la ejecución.
"""

from . import pedidos, requisiciones, sobrecostos

# Mapa de tipos de proceso disponibles para la interfaz.
PROCESADORES = {
    "pedidos": pedidos,
    "requisiciones": requisiciones,
    "sobrecostos": sobrecostos,
}

__all__ = ["pedidos", "requisiciones", "sobrecostos", "PROCESADORES"]

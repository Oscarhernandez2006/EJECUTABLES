"""Paquete de procesadores para la integración con Siesa (Carnes Santa Cruz).

Cada módulo expone una función `procesar(excel_path, work_dir)` que:
  1. Lee el archivo Excel cargado por el usuario.
  2. Genera la trama de texto de posición fija.
  3. Convierte la trama a XML.
  4. Consume el servicio web SOAP de Siesa.

Y devuelve un diccionario con el resultado de la ejecución.
"""

from . import (
    cruce_contable,
    compra_vacuno,
    compra_porcino,
    cargue_lotes,
    canal_vacuno,
    canal_porcino,
    retoma_vacuno,
    retoma_porcino,
    flete_bovino,
    sacrificio_bovino,
    impuestos_sacrificio,
    doc_pedidos,
    compromisos_pedidos,
    # Procesos originales (restaurados desde a415d47).
    pedidos,
    requisiciones,
    sobrecostos,
    transferencia_sc,
)

# Mapa de tipos de proceso disponibles para la interfaz.
PROCESADORES = {
    "compra_vacuno": compra_vacuno,
    "compra_porcino": compra_porcino,
    "cruce_contable": cruce_contable,
    "cargue_lotes": cargue_lotes,
    "canal_vacuno": canal_vacuno,
    "canal_porcino": canal_porcino,
    "retoma_vacuno": retoma_vacuno,
    "retoma_porcino": retoma_porcino,
    "flete_bovino": flete_bovino,
    "sacrificio_bovino": sacrificio_bovino,
    "impuestos_sacrificio": impuestos_sacrificio,
    "doc_pedidos": doc_pedidos,
    "compromisos_pedidos": compromisos_pedidos,
    # Procesos originales (restaurados desde a415d47).
    "pedidos": pedidos,
    "requisiciones": requisiciones,
    "sobrecostos": sobrecostos,
    "transferencia_sc": transferencia_sc,
}

__all__ = ["PROCESADORES"]

"""Transformaciones Taller: salidas SAI y entradas EIN con costo distribuido."""

from .inventario_documentos import procesar_inventario


def procesar(excel_path, work_dir, empresa_id=None, fecha=None, parametros=None, hojas=None):
    return procesar_inventario(
        excel_path, work_dir, empresa_id, fecha, "taller", parametros, hojas,
    )

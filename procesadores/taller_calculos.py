"""Indicadores de transformación equivalentes a la hoja TALLER."""

from decimal import Decimal, InvalidOperation


def decimal_positivo(valor, campo, permitir_cero=False):
    try:
        resultado = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{campo}: debe ser numérico.") from exc
    if not resultado.is_finite() or resultado < 0 or (not permitir_cero and not resultado):
        raise ValueError(f"{campo}: debe ser finito y {'no negativo' if permitir_cero else 'positivo'}.")
    return resultado


def calcular(insumos, productos):
    if not insumos or not productos:
        raise ValueError("Agrega al menos un insumo y un producto terminado.")
    unidades = {str(fila["um"]).strip().lower() for fila in insumos + productos if fila.get("um")}
    if len(unidades) > 1:
        raise ValueError("Los insumos y productos deben tener la misma UM para calcular participación y merma.")
    peso_insumos = sum(decimal_positivo(f["cantidad"], "Cantidad") for f in insumos)
    peso_productos = sum(decimal_positivo(f["cantidad"], "Cantidad") for f in productos)
    costo = sum(decimal_positivo(f["cantidad"], "Cantidad") * decimal_positivo(
        f["costo_promedio"], "Costo promedio", permitir_cero=True) for f in insumos)
    venta = sum(decimal_positivo(f["cantidad"], "Cantidad") * decimal_positivo(
        f["precio_venta"], "Precio de venta", permitir_cero=True) for f in productos)
    if venta <= 0:
        raise ValueError("El valor total de venta debe ser mayor que cero.")
    detalle = []
    for producto in productos:
        cantidad = decimal_positivo(producto["cantidad"], "Cantidad")
        precio = decimal_positivo(producto["precio_venta"], "Precio de venta", permitir_cero=True)
        detalle.append({
            "participacion": float(cantidad / peso_insumos),
            "costo_unitario": float(round(precio * costo / venta, 2)),
            "venta_total": float(cantidad * precio),
        })
    return {
        "costo_total": float(costo), "venta_total": float(venta),
        "utilidad": float(venta - costo), "margen": float((venta - costo) / venta),
        "costo_venta": float(costo / venta), "peso_insumos": float(peso_insumos),
        "peso_productos": float(peso_productos), "merma": float(peso_insumos - peso_productos),
        "rendimiento": float(peso_productos / peso_insumos), "productos": detalle,
    }
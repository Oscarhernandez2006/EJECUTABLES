"""Esquemas de parámetros y de datos escribibles por proceso.

Para cada proceso se definen:
  - ``PARAMETROS_ESQUEMA``: campos de parámetros. La compañía (CIA) NO aparece:
    se toma del selector de empresa.
  - ``CANAL_COLUMNAS``: TODAS las columnas de la hoja CANAL (Excel de ejemplo),
    en orden. En modo manual se muestran todas, se usen o no, para poder pegar
    directamente desde Excel/FrigoApp.
  - ``DATOS_USADAS``: por proceso, las columnas de CANAL que realmente usa/envía;
    solo esas son obligatorias.

Cada campo: ``clave`` (nombre EXACTO de la columna que espera el procesador),
``etiqueta`` (texto visible) y ``tipo`` ("text" o "number").

Un proceso admite el modo manual solo si aparece en ``DATOS_USADAS``.
"""

# ---- Parámetros (además de la compañía) -------------------------------------
PARAMETROS_ESQUEMA = {
    "compra_vacuno": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA", "etiqueta": "Bodega", "tipo": "text"},
        {"clave": "COMPRADOR", "etiqueta": "Tercero comprador", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
        {"clave": "SERVICIO_COMPRA", "etiqueta": "Servicio de compra", "tipo": "text"},
    ],
    "compra_porcino": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA", "etiqueta": "Bodega", "tipo": "text"},
        {"clave": "COMPRADOR", "etiqueta": "Tercero comprador", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
        {"clave": "SERVICIO_COMPRA", "etiqueta": "Servicio de compra", "tipo": "text"},
    ],
    "canal_vacuno": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA", "etiqueta": "Bodega", "tipo": "text"},
    ],
    "canal_porcino": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA", "etiqueta": "Bodega", "tipo": "text"},
    ],
    "retoma_vacuno": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA_PROCESO", "etiqueta": "Bodega de subproductos", "tipo": "text"},
    ],
    "retoma_porcino": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA_SUBPROCESOS", "etiqueta": "Bodega de subprocesos", "tipo": "text"},
        {"clave": "COSTO_VISCERA_ROJA", "etiqueta": "Costo víscera roja", "tipo": "number"},
        {"clave": "COSTO_VISCERA_BLANCA", "etiqueta": "Costo víscera blanca", "tipo": "number"},
        {"clave": "COSTO_CABEZA_CERDO", "etiqueta": "Costo cabeza cerdo", "tipo": "number"},
    ],
    "flete_bovino": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA", "etiqueta": "Bodega", "tipo": "text"},
        {"clave": "COMPRADOR", "etiqueta": "Tercero comprador", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
    ],
    "sacrificio_bovino": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "BODEGA", "etiqueta": "Bodega", "tipo": "text"},
        {"clave": "COMPRADOR", "etiqueta": "Tercero comprador", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
    ],
    "cruce_contable": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
        {"clave": "COMPRADOR", "etiqueta": "Tercero comprador", "tipo": "text"},
        {"clave": "SERVICIO_COMPRA", "etiqueta": "Servicio de compra (1690 = bovino)", "tipo": "text"},
        {"clave": "AUX_DB_VACUNO", "etiqueta": "Auxiliar débito vacuno", "tipo": "text"},
        {"clave": "AUX_CR_VACUNO", "etiqueta": "Auxiliar crédito vacuno", "tipo": "text"},
        {"clave": "AUX_DB_PORCINO", "etiqueta": "Auxiliar débito porcino", "tipo": "text"},
        {"clave": "AUX_CR_PORCINO", "etiqueta": "Auxiliar crédito porcino", "tipo": "text"},
    ],
    # Procesos que solo necesitan la compañía (sin parámetros extra a escribir).
    "cargue_lotes": [],
    "doc_pedidos": [],
    "compromisos_pedidos": [],
    # Procesos por hojas (Pedidos/Requisiciones/Sobrecostos/Transferencia).
    # La CIA sale del selector; el resto se leía por posición de la hoja PARAMETROS.
    "pedidos": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "TERCERO", "etiqueta": "Tercero", "tipo": "text"},
        {"clave": "SOLICITANTE", "etiqueta": "Solicitante", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
        {"clave": "CCOSTOS", "etiqueta": "Centro de costos", "tipo": "text"},
        {"clave": "FECHA", "etiqueta": "Fecha (AAAAMMDD)", "tipo": "text"},
        {"clave": "VENDEDOR", "etiqueta": "Vendedor", "tipo": "text"},
        {"clave": "LISTA_PRECIO", "etiqueta": "Lista de precio", "tipo": "text"},
    ],
    "requisiciones": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "TERCERO", "etiqueta": "Tercero", "tipo": "text"},
        {"clave": "SOLICITANTE", "etiqueta": "Solicitante", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
        {"clave": "CCOSTOS", "etiqueta": "Centro de costos", "tipo": "text"},
        {"clave": "FECHA", "etiqueta": "Fecha (AAAAMMDD)", "tipo": "text"},
        {"clave": "CO_SALIDA", "etiqueta": "CO de salida", "tipo": "text"},
    ],
    "sobrecostos": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "TERCERO", "etiqueta": "Tercero", "tipo": "text"},
        {"clave": "SOLICITANTE", "etiqueta": "Solicitante", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
        {"clave": "CCOSTOS", "etiqueta": "Centro de costos", "tipo": "text"},
        {"clave": "FECHA", "etiqueta": "Fecha (AAAAMMDD)", "tipo": "text"},
        {"clave": "VENDEDOR", "etiqueta": "Vendedor", "tipo": "text"},
        {"clave": "LISTA_PRECIO", "etiqueta": "Lista de precio", "tipo": "text"},
        {"clave": "COMPRADOR", "etiqueta": "Comprador", "tipo": "text"},
    ],
    "transferencia_sc": [
        {"clave": "CO", "etiqueta": "Centro de operación (CO)", "tipo": "text"},
        {"clave": "UN", "etiqueta": "Unidad de negocio (UN)", "tipo": "text"},
        {"clave": "FECHA", "etiqueta": "Fecha (AAAAMMDD)", "tipo": "text"},
        {"clave": "TIPO_DOC", "etiqueta": "Tipo de documento", "tipo": "text"},
    ],
}

# ---- Datos: TODA la hoja CANAL -----------------------------------------------
# ``CANAL_COLUMNAS`` es el listado COMPLETO de columnas de la hoja CANAL del
# Excel de ejemplo (ANALISIS.xlsx), en el mismo orden, para que al pegar desde
# Excel/FrigoApp cada celda caiga en su columna. Se muestran todas, se usen o no.
# Las 5 últimas NO están en el Excel de ejemplo pero SÍ las leen algunos
# ejecutables (compra/flete/sacrificio); se agregan al final para no romperlos.
CANAL_COLUMNAS = [
    {"clave": "FECHA SACRIFICIO", "etiqueta": "Fecha sacrificio", "tipo": "text"},
    {"clave": "LOTE FRIGOAPP", "etiqueta": "Lote FrigoApp", "tipo": "text"},
    {"clave": "PROVEEDOR", "etiqueta": "Proveedor", "tipo": "text"},
    {"clave": "PROCEDENCIA", "etiqueta": "Procedencia", "tipo": "text"},
    {"clave": "TIPO", "etiqueta": "Tipo (FrigoApp)", "tipo": "text"},
    {"clave": "CODIGO", "etiqueta": "Código", "tipo": "text"},
    {"clave": "GANCHO", "etiqueta": "Gancho", "tipo": "text"},
    {"clave": "P. CABEZA", "etiqueta": "P. cabeza", "tipo": "number"},
    {"clave": "PEC(kg)", "etiqueta": "PEC (kg)", "tipo": "number"},
    {"clave": "FRÍO(kg)", "etiqueta": "Frío (kg)", "tipo": "number"},
    {"clave": "REMISION", "etiqueta": "Remisión", "tipo": "number"},
    {"clave": "FECHA SACRIFICIO SIESA", "etiqueta": "Fecha sacrificio SIESA (AAAAMMDD)", "tipo": "text"},
    {"clave": "NIT PROVEEDOR", "etiqueta": "NIT proveedor", "tipo": "text"},
    {"clave": "LOTE", "etiqueta": "Lote", "tipo": "text"},
    {"clave": "CIA", "etiqueta": "CIA", "tipo": "number"},
    {"clave": "AÑO", "etiqueta": "Año", "tipo": "number"},
    {"clave": "MES", "etiqueta": "Mes", "tipo": "number"},
    {"clave": "DIA", "etiqueta": "Día", "tipo": "number"},
    {"clave": "SEMANA", "etiqueta": "Semana", "tipo": "number"},
    {"clave": "N° ANIMAL", "etiqueta": "N° animal", "tipo": "number"},
    {"clave": "CONCEPTO", "etiqueta": "Concepto", "tipo": "text"},
    {"clave": "P.EN PIE", "etiqueta": "P. en pie", "tipo": "number"},
    {"clave": "P PROME EN PIE", "etiqueta": "P. prom. en pie", "tipo": "number"},
    {"clave": "P.CAL + CABEZA", "etiqueta": "P. cal + cabeza", "tipo": "number"},
    {"clave": "% REND", "etiqueta": "% Rend.", "tipo": "number"},
    {"clave": "Merma KG", "etiqueta": "Merma KG", "tipo": "number"},
    {"clave": "Merma %", "etiqueta": "Merma %", "tipo": "number"},
    {"clave": "Estado", "etiqueta": "Estado", "tipo": "text"},
    {"clave": "PESO COMPRA", "etiqueta": "Peso compra", "tipo": "number"},
    {"clave": "P. NEGOCIADO", "etiqueta": "Precio negociado", "tipo": "number"},
    {"clave": "Total a facturar", "etiqueta": "Total a facturar", "tipo": "number"},
    {"clave": "FACTURA PROVEEDOR", "etiqueta": "Factura proveedor", "tipo": "text"},
    {"clave": "sacrificio", "etiqueta": "Sacrificio", "tipo": "number"},
    {"clave": "visceras rojas", "etiqueta": "Vísceras rojas", "tipo": "number"},
    {"clave": "kilos cabeza", "etiqueta": "Kilos cabeza", "tipo": "number"},
    {"clave": "valor cabeza", "etiqueta": "Valor cabeza", "tipo": "number"},
    {"clave": "mondongo", "etiqueta": "Mondongo", "tipo": "number"},
    {"clave": "total costo tat", "etiqueta": "Total costo TAT", "tipo": "number"},
    {"clave": "M. Final", "etiqueta": "M. final", "tipo": "number"},
    {"clave": "%", "etiqueta": "%", "tipo": "number"},
    {"clave": "OTROS CONCEPTOS", "etiqueta": "Otros conceptos", "tipo": "text"},
    {"clave": "FECHA REMISION", "etiqueta": "Fecha remisión", "tipo": "text"},
    {"clave": "COSTO CALIENTE KGR", "etiqueta": "Costo caliente kgr", "tipo": "number"},
    {"clave": "COSTO FRIO KGR", "etiqueta": "Costo frío kgr", "tipo": "number"},
    {"clave": "C.TALLER EN FRIO", "etiqueta": "C. taller en frío", "tipo": "number"},
    {"clave": "C.TALLER EN CALIENTE", "etiqueta": "C. taller en caliente", "tipo": "number"},
    {"clave": "COSTO DE VENTA", "etiqueta": "Costo de venta", "tipo": "number"},
    {"clave": "COSTO MERMA", "etiqueta": "Costo merma", "tipo": "number"},
    {"clave": "INV. UND", "etiqueta": "Inv. und", "tipo": "number"},
    {"clave": "INV. KG", "etiqueta": "Inv. kg", "tipo": "number"},
    {"clave": "COSTO INV", "etiqueta": "Costo inv.", "tipo": "number"},
    {"clave": "NIT CLIENTE ", "etiqueta": "NIT cliente", "tipo": "text"},
    {"clave": "SUCURSAL", "etiqueta": "Sucursal", "tipo": "text"},
    {"clave": "NOMBRE DEL CLIENTE", "etiqueta": "Nombre del cliente", "tipo": "text"},
    {"clave": "DESTINO REMISION", "etiqueta": "Destino remisión", "tipo": "text"},
    {"clave": "FACT. VENTA", "etiqueta": "Fact. venta", "tipo": "text"},
    {"clave": "P.VENTA", "etiqueta": "Precio venta", "tipo": "number"},
    {"clave": "CANTIDAD", "etiqueta": "Cantidad", "tipo": "number"},
    {"clave": "VENTA TOTAL", "etiqueta": "Venta total", "tipo": "number"},
    {"clave": "UTILIDAD", "etiqueta": "Utilidad", "tipo": "number"},
    {"clave": "% CV", "etiqueta": "% CV", "tipo": "number"},
    {"clave": "% UM", "etiqueta": "% UM", "tipo": "number"},
    {"clave": "CARGUE HISTORICO", "etiqueta": "Cargue histórico", "tipo": "text"},
    {"clave": "FECHA PEDIDO SIESA", "etiqueta": "Fecha pedido SIESA (AAAAMMDD)", "tipo": "text"},
    {"clave": "FECHA FACTURA", "etiqueta": "Fecha factura", "tipo": "text"},
    # --- Columnas que NO están en el Excel de ejemplo pero SÍ leen ejecutables ---
    {"clave": "P.PROM FINCA", "etiqueta": "P. prom. finca", "tipo": "number"},
    {"clave": "P.NETO", "etiqueta": "P. neto", "tipo": "number"},
    {"clave": "PESO EN FINCA", "etiqueta": "Peso en finca", "tipo": "number"},
    {"clave": "NIT PROVEEDOR FLETE", "etiqueta": "NIT proveedor flete", "tipo": "text"},
    {"clave": "flete*animal", "etiqueta": "Flete por animal", "tipo": "number"},
    # --- Columnas de subproductos (retoma vacuno), no están en el Excel de ejemplo ---
    {"clave": "K. piel", "etiqueta": "Kilos piel", "tipo": "number"},
    {"clave": "valor piel ", "etiqueta": "Valor piel", "tipo": "number"},
    {"clave": "k. sebo", "etiqueta": "Kilos sebo", "tipo": "number"},
    {"clave": "valor sebo", "etiqueta": "Valor sebo", "tipo": "number"},
    {"clave": "retomas", "etiqueta": "Retomas", "tipo": "number"},
    {"clave": "v.visceras unidad", "etiqueta": "Valor vísceras unidad", "tipo": "number"},
]

# Columnas que cada proceso REALMENTE usa/envía (las demás quedan opcionales).
DATOS_USADAS = {
    "compra_vacuno": [
        "NIT PROVEEDOR", "LOTE", "LOTE FRIGOAPP",
        "FECHA SACRIFICIO SIESA", "P.PROM FINCA", "P.NETO", "Total a facturar",
    ],
    "compra_porcino": [
        "NIT PROVEEDOR", "FACTURA PROVEEDOR", "LOTE", "LOTE FRIGOAPP",
        "FECHA SACRIFICIO SIESA", "PESO COMPRA", "P. NEGOCIADO",
    ],
    "cargue_lotes": [
        "LOTE", "TIPO", "FECHA SACRIFICIO SIESA",
    ],
    "canal_vacuno": [
        "LOTE", "TIPO", "FECHA SACRIFICIO SIESA", "PEC(kg)", "total costo tat",
    ],
    "canal_porcino": [
        "LOTE", "TIPO", "FECHA SACRIFICIO SIESA", "PEC(kg)", "total costo tat",
    ],
    "retoma_vacuno": [
        "TIPO", "LOTE", "FECHA SACRIFICIO SIESA", "PESO EN FINCA",
        "P.NETO", "P.PROM FINCA", "PEC(kg)", "total costo tat",
        "K. piel", "valor piel ", "k. sebo", "valor sebo",
        "retomas", "v.visceras unidad",
    ],
    "retoma_porcino": [
        "CONCEPTO", "TIPO", "LOTE", "FECHA SACRIFICIO SIESA",
        "PESO COMPRA", "PEC(kg)", "total costo tat",
    ],
    "flete_bovino": [
        "NIT PROVEEDOR FLETE", "LOTE", "FECHA SACRIFICIO SIESA",
        "PESO EN FINCA", "flete*animal",
    ],
    "sacrificio_bovino": [
        "LOTE", "FECHA SACRIFICIO SIESA", "PESO EN FINCA", "sacrificio",
    ],
    "cruce_contable": [
        "LOTE", "FECHA SACRIFICIO SIESA", "Total a facturar",
    ],
    "doc_pedidos": [
        "NIT CLIENTE ", "SUCURSAL", "REMISION", "FECHA PEDIDO SIESA",
        "FECHA SACRIFICIO SIESA", "TIPO", "FRÍO(kg)", "P.VENTA", "LOTE",
    ],
    "compromisos_pedidos": [
        "NIT CLIENTE ", "REMISION", "FECHA SACRIFICIO SIESA", "TIPO",
        "FRÍO(kg)", "LOTE",
    ],
}


def esquema_de(proceso_id):
    """Campos de parámetros del proceso (o lista vacía)."""
    return PARAMETROS_ESQUEMA.get(proceso_id, [])


def columnas_usadas_de(proceso_id):
    """Conjunto de columnas CANAL que el proceso usa/envía."""
    return set(DATOS_USADAS.get(proceso_id, []))


def datos_esquema_de(proceso_id):
    """Toda la hoja CANAL como campos; cada uno marcado si el proceso lo usa."""
    if proceso_id not in DATOS_USADAS:
        return []
    usadas = columnas_usadas_de(proceso_id)
    return [{**col, "usado": col["clave"] in usadas} for col in CANAL_COLUMNAS]


def admite_parametros_manuales(proceso_id):
    """Admite modo manual si tiene grilla CANAL o esquema por hojas."""
    return proceso_id in DATOS_USADAS or proceso_id in HOJAS_MANUALES


# ---- Procesos por HOJAS: cada hoja del Excel es una tabla pegable aparte -----
# Para Pedidos/Requisiciones/Sobrecostos/Transferencia el modo manual muestra la
# tabla principal y, debajo, las tablas extra (EQUIVALENTES). Los parámetros
# (CIA del selector + CO/tercero/...) van en el bloque de parámetros.
HOJAS_MANUALES = {
    "pedidos": [
        {"clave": "PEDIDO", "nombre": "Pedido — líneas", "columnas": [
            {"clave": "NUM_DOC", "etiqueta": "Núm. documento", "tipo": "number"},
            {"clave": "N.I.T / C.C.", "etiqueta": "NIT / CC cliente", "tipo": "text"},
            {"clave": "SUCURSAL", "etiqueta": "Sucursal", "tipo": "text"},
            {"clave": "CON_PAGO", "etiqueta": "Cond. de pago", "tipo": "text"},
            {"clave": "CODIGO", "etiqueta": "Código producto", "tipo": "text"},
            {"clave": "BOD SALIDA", "etiqueta": "Bodega salida", "tipo": "text"},
            {"clave": "CANT.(kg)", "etiqueta": "Cantidad (kg)", "tipo": "number"},
        ]},
        {"clave": "EQUIVALENTES", "nombre": "Equivalentes — código → referencia Siesa", "columnas": [
            {"clave": "CODIGO", "etiqueta": "Código producto", "tipo": "text"},
            {"clave": "REF_SIESA", "etiqueta": "Referencia Siesa", "tipo": "text"},
        ]},
    ],
    "requisiciones": [
        {"clave": "TRASNFERENCIA", "nombre": "Requisición — líneas", "columnas": [
            {"clave": "NUM_DOC", "etiqueta": "Núm. documento", "tipo": "number"},
            {"clave": "No.", "etiqueta": "No.", "tipo": "number"},
            {"clave": "BOD ENTRADA", "etiqueta": "Bodega entrada", "tipo": "text"},
            {"clave": "BOD SALIDA", "etiqueta": "Bodega salida", "tipo": "text"},
            {"clave": "CODIGO", "etiqueta": "Código producto", "tipo": "text"},
            {"clave": "CANT.(kg)", "etiqueta": "Cantidad (kg)", "tipo": "number"},
        ]},
        {"clave": "EQUIVALENTES", "nombre": "Equivalentes — código → referencia Siesa", "columnas": [
            {"clave": "CODIGO", "etiqueta": "Código producto", "tipo": "text"},
            {"clave": "REF_SIESA", "etiqueta": "Referencia Siesa", "tipo": "text"},
        ]},
    ],
    "sobrecostos": [
        {"clave": "SOBRECOSTOS", "nombre": "Sobrecostos — líneas", "columnas": [
            {"clave": "NUM_DOC", "etiqueta": "Núm. documento", "tipo": "number"},
            {"clave": "N.I.T / C.C.", "etiqueta": "NIT / CC cliente", "tipo": "text"},
            {"clave": "SUCURSAL", "etiqueta": "Sucursal", "tipo": "text"},
            {"clave": "TIPO_DOC_BASE", "etiqueta": "Tipo doc. base", "tipo": "text"},
            {"clave": "NUM_DOC_BASE", "etiqueta": "Núm. doc. base", "tipo": "number"},
            {"clave": "VALOR", "etiqueta": "Valor", "tipo": "number"},
            {"clave": "DESCRIPCION", "etiqueta": "Descripción", "tipo": "text"},
            {"clave": "REF_SOBRECOSTOS", "etiqueta": "Referencia sobrecosto", "tipo": "text"},
        ]},
    ],
    "transferencia_sc": [
        {"clave": "DESPOSTE", "nombre": "Desposte — líneas", "columnas": [
            {"clave": "BODEGA ORIGEN", "etiqueta": "Bodega origen", "tipo": "text"},
            {"clave": "BODEGA DESTINO", "etiqueta": "Bodega destino", "tipo": "text"},
            {"clave": "LOTE", "etiqueta": "Lote", "tipo": "text"},
            {"clave": "TIPO", "etiqueta": "Tipo (producto)", "tipo": "text"},
            {"clave": "FRÍO(kg)", "etiqueta": "Frío (kg)", "tipo": "number"},
        ]},
        {"clave": "EQUIVALENTES", "nombre": "Equivalentes — producto → referencia Siesa", "columnas": [
            {"clave": "PRODUCTO", "etiqueta": "Producto", "tipo": "text"},
            {"clave": "REF_SIESA", "etiqueta": "Referencia Siesa", "tipo": "text"},
        ]},
    ],
}


def hojas_manuales_de(proceso_id):
    """Hojas (tablas) del modo manual por hojas, o lista vacía."""
    return HOJAS_MANUALES.get(proceso_id, [])

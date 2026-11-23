"""Lectura y tramas 450/470 compartidas por Taller y saldos iniciales."""

import os
from decimal import Decimal, InvalidOperation

import pandas as pd

from . import siesa


COLUMNAS = ["CO", "TIPO_DOC", "NUMERO", "LOTE", "REFERENCIA", "BODEGA", "UM", "CANT"]
CLAVE_DOCUMENTO = ["CO", "TIPO_DOC", "NUMERO"]
CLAVE_TALLER = ["CO", "NUMERO"]


def texto(valor, campo, ancho, obligatorio=True):
    valor = siesa.codigo(valor)
    if (obligatorio and not valor) or len(valor) > ancho or any(c in valor for c in "\r\n\t"):
        raise ValueError(f"{campo}: debe contener {'entre 1 y' if obligatorio else 'hasta'} "
                         f"{ancho} caracteres, sin saltos de línea ni tabulaciones.")
    return valor


def numero(valor, campo, positivo=False, entero=False):
    try:
        valor = Decimal(str(valor))
    except InvalidOperation as exc:
        raise ValueError(f"{campo}: debe ser numérico.") from exc
    if not valor.is_finite() or valor < 0 or (positivo and valor == 0):
        raise ValueError(f"{campo}: debe ser finito y {'positivo' if positivo else 'no negativo'}.")
    if entero and (valor != valor.to_integral_value() or valor > 99999999):
        raise ValueError(f"{campo}: debe ser un entero de hasta 8 dígitos.")
    if not entero:
        if len(f"{valor:020.4f}") > 20 or (positivo and round(valor, 4) == 0):
            raise ValueError(f"{campo}: no cabe en el campo Siesa de 20 posiciones y 4 decimales.")
    return int(valor) if entero else valor


class DocumentosInventario:
    def __init__(self, excel_path, empresa_id, fecha, proceso, parametros=None, hojas=None):
        if not empresa_id:
            raise ValueError("Debes seleccionar la empresa.")
        if (not fecha or len(str(fecha)) != 8 or not str(fecha).isdigit()
                or pd.isna(pd.to_datetime(str(fecha), format="%Y%m%d", errors="coerce"))):
            raise ValueError("Debes indicar una fecha válida (AAAAMMDD).")
        self.cia = int(empresa_id)
        self.fecha = str(fecha)
        self.proceso = proceso
        self.un = texto((parametros or {}).get("UN", "001"), "UN", 20)
        tercero = "900326452" if proceso == "taller" else "generico"
        self.tercero = texto((parametros or {}).get("TERCERO", tercero), "TERCERO", 15)
        costo = "COSTO UNITARIO" if proceso == "taller" else "COSTO_UNITARIO"
        columnas = COLUMNAS + [costo]
        if proceso == "taller":
            columnas.append("PRECIO DE  VENTA")
        if hojas is not None:
            datos = siesa.hoja_df(hojas, "Hoja1")
        else:
            datos = siesa.leer_hoja(
                excel_path, "Hoja1",
                dtype={c: str for c in ("CO", "TIPO_DOC", "LOTE", "REFERENCIA", "BODEGA", "UM")},
            )
        datos = siesa.alinear_columnas(datos, [c for c in columnas if c not in datos.columns])
        datos = datos.dropna(how="all").copy()
        siesa.exigir_datos(datos, "La hoja Hoja1 no tiene movimientos de inventario.")
        faltantes = [c for c in columnas if c not in datos.columns]
        if faltantes:
            raise ValueError("Faltan columnas en Hoja1: " + ", ".join(faltantes) + ".")
        if "CIA" in datos.columns:
            for cia in datos["CIA"].unique():
                if hojas is not None and not siesa.codigo(cia):
                    continue
                siesa.validar_empresa(cia, empresa_id)
        self.datos = datos
        self.validar(costo)
        if proceso == "taller":
            self.calcular_taller()
        else:
            self.datos["COSTO_CALCULADO"] = self.datos[costo]

    def validar(self, costo):
        anchos = {"CO": 3, "TIPO_DOC": 3, "LOTE": 15, "REFERENCIA": 50, "BODEGA": 5, "UM": 4}
        for campo, ancho in anchos.items():
            self.datos[campo] = self.datos[campo].map(
                lambda v: texto(v, campo, ancho, obligatorio=campo != "LOTE")
            )
        self.datos["UM"] = self.datos["UM"].str.lower()
        self.datos["NUMERO"] = self.datos["NUMERO"].map(
            lambda v: numero(v, "NUMERO", positivo=True, entero=True)
        )
        self.datos["CANT"] = self.datos["CANT"].map(lambda v: numero(v, "CANT", positivo=True))
        tipos = {"SAI", "EIN"} if self.proceso == "taller" else {"SIN"}
        invalidos = set(self.datos["TIPO_DOC"]) - tipos
        if invalidos:
            raise ValueError(f"TIPO_DOC no permitido: {', '.join(sorted(invalidos))}. "
                             f"Para este proceso usa {', '.join(sorted(tipos))}.")
        entradas = self.datos["TIPO_DOC"] != "SAI"
        # El costo de las entradas de Taller se calcula; la plantilla lo deja vacío.
        requeridos = ~entradas if self.proceso == "taller" else entradas
        self.datos[costo] = self.datos[costo].astype(object)
        self.datos.loc[requeridos, costo] = self.datos.loc[requeridos, costo].map(
            lambda v: numero(v, costo)
        )
        if self.proceso == "taller":
            self.datos["PRECIO DE  VENTA"] = self.datos["PRECIO DE  VENTA"].astype(object)
            self.datos.loc[entradas, "PRECIO DE  VENTA"] = self.datos.loc[
                entradas, "PRECIO DE  VENTA"
            ].map(lambda v: numero(v, "PRECIO DE VENTA"))

    def calcular_taller(self):
        salida = self.datos[self.datos["TIPO_DOC"] == "SAI"].copy()
        entrada = self.datos[self.datos["TIPO_DOC"] == "EIN"].copy()
        grupos_salida = set(map(tuple, salida[CLAVE_TALLER].to_numpy()))
        grupos_entrada = set(map(tuple, entrada[CLAVE_TALLER].to_numpy()))
        if grupos_salida != grupos_entrada or not grupos_salida:
            faltan = sorted(grupos_salida ^ grupos_entrada)
            detalle = ", ".join(f"CO {co}, NUMERO {n}" for co, n in faltan)
            raise ValueError("Cada transformación de Taller debe tener salidas SAI y entradas EIN "
                             f"con el mismo CO y NUMERO. Revisa: {detalle or 'no hay parejas'}.")
        salida["COSTO_TOTAL"] = salida["COSTO UNITARIO"] * salida["CANT"]
        entrada["VENTA"] = entrada["PRECIO DE  VENTA"] * entrada["CANT"]
        costos = salida.groupby(CLAVE_TALLER)["COSTO_TOTAL"].sum()
        ventas = entrada.groupby(CLAVE_TALLER)["VENTA"].transform("sum")
        if (ventas <= 0).any():
            raise ValueError("El total de PRECIO DE VENTA por cantidad debe ser positivo en cada transformación.")
        costo_entrada = pd.Series(
            [costos.loc[tuple(f)] for f in entrada[CLAVE_TALLER].to_numpy()],
            index=entrada.index, dtype=object,
        )
        entrada["COSTO_CALCULADO"] = [
            round(precio * costo / venta, 2)
            for precio, costo, venta in zip(entrada["PRECIO DE  VENTA"], costo_entrada, ventas)
        ]
        salida["COSTO_CALCULADO"] = Decimal(0)
        self.datos = pd.concat([salida, entrada])
        for costo in self.datos["COSTO_CALCULADO"]:
            numero(costo, "COSTO_CALCULADO")

    def encabezado(self, fila, consecutivo):
        salida = fila["TIPO_DOC"] == "SAI"
        nota = "SALDOS INICIALES DE INVENTARIOS" if self.proceso == "siinv" else ""
        return (
            f"{consecutivo:07d}04500002{self.cia:03d}1"
            + f"{fila['CO']:3}{fila['TIPO_DOC']:3}{fila['NUMERO']:08d}{self.fecha:8}"
            + f"{self.tercero:15}{62 if salida else 61:03d}00"
            + " " * 255 + f"{602 if salida else 601:03d}"
            + " " * 31 + "00000000" + " " * 108
            + "0" * 105 + f"{nota:255}"
        )

    def movimiento(self, fila, consecutivo, registro):
        salida = fila["TIPO_DOC"] == "SAI"
        concepto = 602 if salida else 601
        motivo = "04" if self.proceso == "taller" else "99"
        nota = "TALLER" if self.proceso == "taller" else "SALDOS INICIALES DE INVENTARIO"
        return (
            f"{consecutivo:07d}04700012{self.cia:03d}"
            + f"{fila['CO']:3}{fila['TIPO_DOC']:3}{fila['NUMERO']:08d}{registro:010d}"
            + " " * 55 + f"{fila['BODEGA']:5}" + " " * 10
            + f"{fila['LOTE']:15}{concepto:03d}{motivo:2}{fila['CO']:3}"
            + " " * 32 + f"{fila['UM']:4}{fila['CANT']:020.4f}"
            + f"{0:020.4f}{fila['COSTO_CALCULADO']:020.4f}{nota:255}"
            + " " * 2054 + f"{fila['LOTE']:15}{0:7}{fila['REFERENCIA']:<50}"
            + " " * 60 + f"{self.un:20}{0:010d}"
        )

    def generar_trama(self):
        bloques = []
        c, registro = 2, 1
        # Una transformación completa permanece en la misma petición SOAP.
        grupos = self.datos.groupby(
            CLAVE_TALLER if self.proceso == "taller" else CLAVE_DOCUMENTO, sort=False,
        )
        for _, grupo in grupos:
            bloque = []
            for _, documento in grupo.groupby(CLAVE_DOCUMENTO, sort=False):
                bloque.append(self.encabezado(documento.iloc[0], c))
                c += 1
                for _, fila in documento.iterrows():
                    bloque.append(self.movimiento(fila, c, registro))
                    c += 1
                    registro += 1
            bloques.append(bloque)
        self.bloques = bloques
        self.trama = [f"000000100000001{self.cia:03d}"]
        self.trama.extend(linea for bloque in bloques for linea in bloque)
        self.trama.append(f"{c:07d}99990001{self.cia:03d}")


def procesar_inventario(excel_path, work_dir, empresa_id, fecha, proceso, parametros=None, hojas=None):
    siesa.reportar_progreso(5, "Leyendo movimientos de inventario…")
    proc = DocumentosInventario(excel_path, empresa_id, fecha, proceso, parametros, hojas)
    proc.generar_trama()
    nombre = "Taller.txt" if proceso == "taller" else "INV_SALDOS_INICIALES.txt"
    siesa.guardar_trama(proc.trama, os.path.join(work_dir, nombre))
    siesa.reportar_progreso(15, "Movimientos validados. Preparando envío…")
    prefijo = "SIESA_TALLER" if proceso == "taller" else "SIESA_SIINV"
    resultado = siesa.enviar_por_lotes(
        proc.bloques, proc.cia, str(proc.cia), work_dir,
        os.getenv(prefijo + "_USER", siesa.SIESA_USER),
        os.getenv(prefijo + "_PASSWORD", siesa.SIESA_PASSWORD),
    )
    resultado.update(registros=len(proc.datos), trama_txt="\n".join(proc.trama) + "\n",
                     trama_nombre=nombre)
    return resultado

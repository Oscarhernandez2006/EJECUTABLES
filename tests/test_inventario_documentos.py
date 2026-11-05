import io
import json
import os
import tempfile
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import pandas as pd

from app import app, PROCESOS, PLANTILLAS_DIR
from config.esquemas import hojas_manuales_de
from procesadores import PROCESADORES, siesa, siinv, taller
from procesadores.inventario_documentos import DocumentosInventario


FECHA = "20261105"


def fila(tipo="SIN", numero=1, **cambios):
    datos = {
        "CIA": 4, "FECHA": "20260131", "CO": "402", "TIPO_DOC": tipo,
        "NUMERO": numero, "LOTE": None, "REFERENCIA": "000123", "BODEGA": "40201",
        "UM": "KG  ", "CANT": 10, "COSTO_UNITARIO": 25,
        "COSTO UNITARIO": 100 if tipo == "SAI" else None,
        "PRECIO DE  VENTA": 50 if tipo == "EIN" else None,
    }
    datos.update(cambios)
    return datos


def preparar(filas, proceso="siinv"):
    return DocumentosInventario(
        None, "4", FECHA, proceso, hojas={"Hoja1": filas},
    )


def excel_bytes(filas):
    archivo = io.BytesIO()
    pd.DataFrame(filas).to_excel(archivo, sheet_name="Hoja1", index=False)
    archivo.seek(0)
    return archivo


class InventarioTests(unittest.TestCase):
    def test_siinv_conserva_campos_y_estructura_original(self):
        proc = preparar([fila(LOTE="00001-003")])
        proc.generar_trama()
        self.assertEqual(list(map(len, proc.trama)), [18, 826, 2702, 18])
        cabecera, detalle = proc.trama[1:3]
        self.assertEqual(cabecera[7:18], "04500002004")
        self.assertEqual(cabecera[33:41], FECHA)
        self.assertEqual(cabecera[56:59], "061")
        self.assertEqual(cabecera[316:319], "601")
        self.assertEqual(detalle[112:127].strip(), "00001-003")
        self.assertEqual(detalle[127:132], "60199")
        self.assertEqual(detalle[167:171].strip(), "kg")
        self.assertEqual(Decimal(detalle[171:191]), Decimal(10))
        self.assertEqual(Decimal(detalle[211:231]), Decimal(25))
        self.assertEqual(detalle[2540:2555].strip(), "00001-003")
        self.assertEqual(detalle[2562:2612].strip(), "000123")
        self.assertEqual(detalle[2672:2692].strip(), "001")

    def test_taller_suma_todas_las_salidas_y_distribuye_por_venta(self):
        proc = preparar([
            fila("SAI", CANT=2, **{"COSTO UNITARIO": 100}),
            fila("SAI", CANT=3, **{"COSTO UNITARIO": 200}),
            fila("EIN", CANT=4, **{"PRECIO DE  VENTA": 50}),
            fila("EIN", CANT=6, **{"PRECIO DE  VENTA": 100}),
        ], "taller")
        self.assertEqual(proc.datos["COSTO_CALCULADO"].tolist(),
                         [Decimal(0), Decimal(0), Decimal("50.00"), Decimal("100.00")])
        entradas = proc.datos[proc.datos["TIPO_DOC"] == "EIN"]
        self.assertEqual((entradas["CANT"] * entradas["COSTO_CALCULADO"]).sum(), Decimal(800))
        proc.generar_trama()
        self.assertEqual(len(proc.bloques), 1)
        self.assertEqual(Counter(r[7:11] for r in proc.trama), {
            "0000": 1, "0450": 2, "0470": 4, "9999": 1,
        })
        self.assertEqual(proc.bloques[0][0][56:59], "062")
        self.assertEqual(proc.bloques[0][0][316:319], "602")

    def test_no_cruza_costos_entre_centros_o_transformaciones(self):
        filas = []
        for co, n, costo in (("402", 1, 100), ("403", 1, 200), ("402", 2, 300)):
            filas.extend([
                fila("SAI", numero=n, CO=co, **{"COSTO UNITARIO": costo}),
                fila("EIN", numero=n, CO=co),
            ])
        proc = preparar(filas, "taller")
        self.assertEqual(proc.datos.loc[proc.datos["TIPO_DOC"] == "EIN", "COSTO_CALCULADO"].tolist(),
                         [Decimal("100.00"), Decimal("200.00"), Decimal("300.00")])
        proc.generar_trama()
        self.assertEqual(len(proc.bloques), 3)

    def test_documentos_con_mismo_numero_y_distinto_co_tienen_encabezados(self):
        proc = preparar([fila(), fila(CO="403")])
        proc.generar_trama()
        self.assertEqual(len(proc.bloques), 2)

    def test_lote_vacio_no_se_convierte_en_nan(self):
        for lote in (None, float("nan"), "", " "):
            with self.subTest(lote=lote):
                proc = preparar([fila(LOTE=lote)])
                proc.generar_trama()
                self.assertEqual(proc.trama[2][112:127], " " * 15)

    def test_errores_impiden_envio(self):
        casos = [
            ({"CIA": 7}, "seleccionaste"),
            ({"TIPO_DOC": "EIN"}, "TIPO_DOC"),
            ({"LOTE": "1234567890123456"}, "LOTE"),
            ({"REFERENCIA": None}, "REFERENCIA"),
            ({"BODEGA": "123456"}, "BODEGA"),
            ({"CO": "1234"}, "CO"),
            ({"UM": "KG\nX"}, "UM"),
            ({"NUMERO": 1.5}, "NUMERO"),
            ({"NUMERO": 0}, "NUMERO"),
            ({"NUMERO": 100000000}, "NUMERO"),
            ({"CANT": 0}, "CANT"),
            ({"CANT": 0.00001}, "CANT"),
            ({"CANT": float("inf")}, "CANT"),
            ({"COSTO_UNITARIO": -1}, "COSTO_UNITARIO"),
            ({"COSTO_UNITARIO": "incorrecto"}, "COSTO_UNITARIO"),
            ({"COSTO_UNITARIO": float("nan")}, "COSTO_UNITARIO"),
            ({"COSTO_UNITARIO": 10**20}, "COSTO_UNITARIO"),
        ]
        for cambios, mensaje in casos:
            with self.subTest(cambios=cambios):
                with tempfile.TemporaryDirectory() as work_dir:
                    with patch.object(siesa, "consumir_servicio_web") as servicio:
                        with self.assertRaisesRegex(ValueError, mensaje):
                            siinv.procesar(None, work_dir, "4", FECHA, hojas={"Hoja1": [fila(**cambios)]})
                        servicio.assert_not_called()

    def test_taller_rechaza_parejas_incompletas_y_valores_vacios(self):
        casos = [
            [fila("SAI")], [fila("EIN")],
            [fila("SAI"), fila("EIN", numero=2)],
            [fila("SAI", **{"COSTO UNITARIO": None}), fila("EIN")],
            [fila("SAI"), fila("EIN", **{"PRECIO DE  VENTA": 0})],
        ]
        for filas in casos:
            with self.subTest(filas=filas), self.assertRaises(ValueError):
                preparar(filas, "taller")

    def test_rechaza_fecha_invalida_o_hoja_vacia_o_columnas_faltantes(self):
        for fecha in (None, "20260230", "202611", "abcdefgh"):
            with self.assertRaisesRegex(ValueError, "fecha"):
                DocumentosInventario(None, "4", fecha, "siinv", hojas={"Hoja1": [fila()]})
        with self.assertRaisesRegex(ValueError, "no tiene movimientos"):
            preparar([])
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            preparar([{"CO": "402"}])

    def test_lectura_excel_conserva_ceros_iniciales(self):
        with tempfile.TemporaryDirectory() as work_dir:
            archivo = Path(work_dir, "saldos.xlsx")
            archivo.write_bytes(excel_bytes([fila(LOTE="001-002")]).getvalue())
            proc = DocumentosInventario(archivo, "4", FECHA, "siinv")
            self.assertEqual(proc.datos["REFERENCIA"].iloc[0], "000123")
            self.assertEqual(proc.datos["LOTE"].iloc[0], "001-002")

    def test_lotes_sin_partir_transformaciones_y_xml_valido(self):
        filas = [fila("SAI"), fila("EIN"), fila("SAI", numero=2), fila("EIN", numero=2)]
        envios = []

        def simular(ruta):
            xml = ElementTree.parse(ruta).getroot()
            lineas = [r.text.rstrip("\n") for r in xml.find("Datos")]
            envios.append(lineas)
            self.assertEqual(xml.findtext("IdCia"), "4")
            return {"ok": True, "mensaje": "Simulado"}

        with tempfile.TemporaryDirectory() as work_dir:
            with patch.object(siesa, "LOTE_LINEAS", 2), \
                 patch.object(siesa, "consumir_servicio_web", side_effect=simular):
                resultado = taller.procesar(
                    None, work_dir, "4", FECHA, hojas={"Hoja1": filas},
                )
            self.assertTrue(resultado["ok"])
            self.assertEqual(resultado["registros"], 4)
            self.assertTrue(Path(work_dir, "Taller.txt").exists())
        self.assertEqual(len(envios), 2)
        for n, lineas in enumerate(envios, 1):
            self.assertEqual([int(r[:7]) for r in lineas], list(range(1, len(lineas) + 1)))
            self.assertEqual({r[21:24] for r in lineas if r[7:11] == "0470"}, {"SAI", "EIN"})
            self.assertEqual({int(r[24:32]) for r in lineas if r[7:11] == "0470"}, {n})


class WebInventarioTests(unittest.TestCase):
    def test_catalogo_y_pagina_incluyen_ambos_procesos(self):
        with app.test_client() as client:
            pagina = client.get("/")
            self.assertEqual(pagina.status_code, 200)
            for proceso in ("taller", "siinv"):
                self.assertIn(proceso, PROCESADORES)
                self.assertIn(proceso.encode(), pagina.data)
                self.assertTrue(hojas_manuales_de(proceso))

    def test_api_excel_y_manual_sin_envios_reales(self):
        with app.test_client() as client, \
             patch.object(siesa, "consumir_servicio_web", return_value={"ok": True, "mensaje": "Simulado"}):
            for proceso, filas in (
                ("siinv", [fila()]), ("taller", [fila("SAI"), fila("EIN")]),
            ):
                for modo in ("excel", "manual"):
                    with self.subTest(proceso=proceso, modo=modo):
                        datos = {"empresa": "4", "fecha": FECHA, "modo_parametros": modo}
                        if modo == "excel":
                            datos["archivo"] = (excel_bytes(filas), "carga.xlsx")
                        else:
                            datos.update(param_UN="001", param_TERCERO="generico")
                            sin_opcionales = [
                                {k: v for k, v in f.items() if k not in {"CIA", "FECHA", "LOTE"}}
                                for f in filas
                            ]
                            datos["hojas"] = json.dumps({"Hoja1": sin_opcionales})
                        respuesta = client.post("/api/procesar/" + proceso, data=datos)
                        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
                        self.assertTrue(respuesta.get_json()["ok"], respuesta.get_json())
                        self.assertEqual(respuesta.get_json()["registros"], len(filas))
                        self.assertTrue(respuesta.get_json()["trama_txt"])

    def test_error_se_muestra_en_web_sin_conectar_a_siesa(self):
        with app.test_client() as client, patch.object(siesa, "consumir_servicio_web") as servicio:
            respuesta = client.post("/api/procesar/taller", data={
                "empresa": "4", "fecha": FECHA,
                "archivo": (excel_bytes([fila("SAI")]), "taller.xlsx"),
            })
            self.assertEqual(respuesta.status_code, 400)
            self.assertIn("entradas EIN", respuesta.get_json()["mensaje"])
            servicio.assert_not_called()

    def test_todas_las_plantillas_del_catalogo_se_descargan(self):
        with app.test_client() as client:
            for proceso in PROCESOS:
                for entrada in proceso["entradas"]:
                    with self.subTest(proceso=proceso["id"], clave=entrada["clave"]):
                        self.assertTrue(os.path.isfile(os.path.join(PLANTILLAS_DIR, entrada["archivo"])))
                        respuesta = client.get(f"/plantilla/{proceso['id']}/{entrada['clave']}")
                        self.assertEqual(respuesta.status_code, 200)
                        respuesta.close()

    def test_plantillas_nuevas_generan_trama(self):
        for proceso, nombre, cia, total in (
            ("taller", "Taller.xlsx", "6", 15),
            ("siinv", "PLANT3.xlsx", "4", 142),
        ):
            with self.subTest(proceso=proceso):
                proc = DocumentosInventario(os.path.join(PLANTILLAS_DIR, nombre), cia, FECHA, proceso)
                proc.generar_trama()
                self.assertEqual(len(proc.datos), total)
                for linea in proc.trama:
                    self.assertEqual(len(linea), {"0000": 18, "9999": 18, "0450": 826, "0470": 2702}[linea[7:11]])


if __name__ == "__main__":
    unittest.main()

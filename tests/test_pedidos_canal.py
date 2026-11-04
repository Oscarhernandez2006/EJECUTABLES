import os
import tempfile
import unittest
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from procesadores import compromisos_pedidos, doc_pedidos, siesa


PESO = "FR\u00cdO(kg)"
FECHA = "20261031"
CLASES = (doc_pedidos.DocPedidos, compromisos_pedidos.CompromisosPedidos)
REFERENCIAS = pd.DataFrame({"FRIGOAPP": ["CERDO", "VACA"], "SIESA": ["2003", "1983"]})


def canal(lote="28746-473", remision=10, tipo="CERDO", peso=87.024, **cambios):
    fila = {
        "CIA": 3,
        "NIT CLIENTE ": "CLIENTE_PRUEBA",
        "SUCURSAL": "001",
        "REMISION": remision,
        "FECHA PEDIDO SIESA": FECHA,
        "FECHA SACRIFICIO SIESA": FECHA,
        "TIPO": tipo,
        "LOTE": lote,
        PESO: peso,
        "P.VENTA": 10000,
    }
    fila.update(cambios)
    return fila


def preparar(clase, filas):
    with patch.object(pd, "read_excel", return_value=REFERENCIAS.copy()):
        proc = clase(None, ".", "3", FECHA, parametros={}, datos=filas)
    proc.mapeo_referencias()
    proc.dataframe()
    proc.dataframe2()
    proc.generar_trama()
    return proc


def movimientos(lineas):
    return {
        (int(r[24:32]), int(r[32:42])): (r[49:99].strip(), Decimal(r[241:261]))
        for r in lineas if r[7:11] == "0431"
    }


def compromisos(lineas):
    return [
        (int(r[24:32]), int(r[223:233]), r[39:89].strip(),
         r[164:179].strip(), Decimal(r[183:203]))
        for r in lineas if r[7:11] == "0405"
    ]


class CorrespondenciaMixin:
    def comprobar_correspondencia(self, pedidos, reservas, filas):
        detalle = movimientos(pedidos)
        recibido = compromisos(reservas)
        totales = defaultdict(Decimal)
        esperado = sorted(
            (int(f["REMISION"]), f["LOTE"].strip(), Decimal(str(round(float(f[PESO]), 2))))
            for f in filas
        )
        self.assertEqual(sorted((r, lote, kg) for r, _, _, lote, kg in recibido), esperado)
        for remision, numero, referencia, lote, kilos in recibido:
            self.assertIn((remision, numero), detalle, lote)
            self.assertEqual(detalle[remision, numero][0], referencia, lote)
            totales[remision, numero] += kilos
        self.assertEqual(dict(totales), {k: v[1] for k, v in detalle.items()})


class PedidosCanalTests(CorrespondenciaMixin, unittest.TestCase):
    def test_varios_ganchos_comparten_el_movimiento_agrupado(self):
        filas = [canal(), canal("28746-474", peso=95.452)]
        pedido = preparar(CLASES[0], filas)
        reserva = preparar(CLASES[1], filas)
        self.assertEqual(len(pedido.data_mov), 1)
        self.assertEqual([r[1] for r in compromisos(reserva.d0)], [1, 1])
        self.comprobar_correspondencia(pedido.d0, reserva.d0, filas)

    def test_remisiones_y_referencias_intercaladas_no_desplazan_ganchos(self):
        filas = [
            canal("28746-480", 20),
            canal("28746-475", 10, "VACA"),
            canal("28746-479", 20, "VACA"),
            canal("28746-473", 10),
            canal("28746-476", 10, "VACA"),
        ]
        pedido = preparar(CLASES[0], filas)
        reserva = preparar(CLASES[1], filas)
        self.comprobar_correspondencia(pedido.d0, reserva.d0, filas)
        for row in pedido.d0:
            if row[7:11] == "0431":
                self.assertEqual(len(row), 2559)
        for row in reserva.d0[1:-1]:
            self.assertEqual(len(row), 233)

    def test_filtrar_filas_no_renumera_por_indice_excel(self):
        filas = [
            canal("28746-470", **{"FECHA PEDIDO SIESA": "20261030"}),
            canal("28746-473"),
            canal("28746-474"),
        ]
        pedido = preparar(CLASES[0], filas)
        reserva = preparar(CLASES[1], filas)
        self.comprobar_correspondencia(pedido.d0, reserva.d0, filas[1:])

    def test_conserva_lote_con_ceros_y_limite_de_15_caracteres(self):
        for lote in ("00028746-00473", "123456789-12345"):
            for clase in CLASES:
                with self.subTest(lote=lote, clase=clase.__name__):
                    proc = preparar(clase, [canal(lote)])
                    self.assertEqual(proc.data1["LOTE"].iloc[0], lote)

    def test_rechaza_lotes_vacios_malformados_o_que_antes_se_recortaban(self):
        for lote in (None, float("nan"), "", "   ", "28746", "28746-", "-473",
                     "28746 473", "28746-\n473", "1234567890-12345", 28746):
            for clase in CLASES:
                with self.subTest(lote=lote, clase=clase.__name__):
                    with self.assertRaisesRegex(ValueError, "LOTE"):
                        preparar(clase, [canal(lote)])

    def test_verifica_gancho_y_lote_frigoapp_de_la_misma_fila(self):
        for columna, valor in (("GANCHO", 474), ("LOTE FRIGOAPP", 28751)):
            for clase in CLASES:
                with self.subTest(columna=columna, clase=clase.__name__):
                    with self.assertRaisesRegex(ValueError, columna):
                        preparar(clase, [canal(**{columna: valor})])
        for clase in CLASES:
            proc = preparar(clase, [canal(**{"GANCHO": 473.0, "LOTE FRIGOAPP": 28746.0})])
            self.assertEqual(proc.data1["LOTE"].iloc[0], "28746-473")

    def test_no_inventa_lote_a_partir_del_gancho(self):
        for clase in CLASES:
            with self.assertRaisesRegex(ValueError, "LOTE"):
                preparar(clase, [canal(None, **{"GANCHO": 473, "LOTE FRIGOAPP": 28746})])

    def test_no_valida_lotes_de_otras_fechas(self):
        for clase in CLASES:
            proc = preparar(clase, [
                canal(None, **{"FECHA PEDIDO SIESA": "20261030"}),
                canal("28746-474"),
            ])
            self.assertEqual(proc.data1["LOTE"].tolist(), ["28746-474"])

    def test_mantiene_filtro_alternativo_por_sacrificio(self):
        for clase in CLASES:
            proc = preparar(clase, [canal(**{"FECHA PEDIDO SIESA": None})])
            self.assertEqual(len(proc.data1), 1)

    def test_rechaza_peso_invalido_incluso_despues_de_redondear(self):
        for peso in (None, 0, -1, "incorrecto", float("inf"), 0.001):
            for clase in CLASES:
                with self.subTest(peso=peso, clase=clase.__name__):
                    with self.assertRaisesRegex(ValueError, "Peso"):
                        preparar(clase, [canal(peso=peso)])

    def test_rechaza_remision_fraccionaria_o_fuera_del_ancho(self):
        for remision in (0, -1, 10.5, 100000000, float("inf"), "incorrecta"):
            for clase in CLASES:
                with self.subTest(remision=remision, clase=clase.__name__):
                    with self.assertRaisesRegex(ValueError, "REMISION"):
                        preparar(clase, [canal(remision=remision)])

    def test_agrupa_remision_numerica_y_texto_como_el_mismo_documento(self):
        filas = [canal(remision=10), canal("28746-474", remision="10")]
        pedido = preparar(CLASES[0], filas)
        reserva = preparar(CLASES[1], filas)
        self.assertEqual(len(pedido.bloques), 1)
        self.comprobar_correspondencia(pedido.d0, reserva.d0, filas)

    def test_rechaza_datos_que_se_perdian_al_tomar_el_primer_valor(self):
        for campo, valor in (("NIT CLIENTE ", "OTRO_CLIENTE"), ("SUCURSAL", "002"),
                             ("FECHA SACRIFICIO SIESA", "20261030"), ("P.VENTA", 12000)):
            for clase in CLASES:
                with self.subTest(campo=campo, clase=clase.__name__):
                    with self.assertRaisesRegex(ValueError, campo.strip().replace(".", r"\.")):
                        preparar(clase, [canal(), canal("28746-474", **{campo: valor})])

    def test_compromisos_manuales_no_exigen_precio_ni_sucursal(self):
        fila = canal()
        del fila["P.VENTA"]
        del fila["SUCURSAL"]
        proc = preparar(CLASES[1], [fila])
        self.assertEqual(compromisos(proc.d0)[0][3], fila["LOTE"])

    def test_documentos_convierten_precio_textual_sin_alterar_trama(self):
        proc = preparar(CLASES[0], [canal(**{"P.VENTA": "10000"})])
        row = next(r for r in proc.d0 if r[7:11] == "0431")
        self.assertEqual(Decimal(row[281:301]), Decimal("10000"))

    def test_rechaza_precio_invalido(self):
        for precio in (None, 0, -1, float("inf"), "incorrecto"):
            with self.subTest(precio=precio):
                with self.assertRaisesRegex(ValueError, "Precio"):
                    preparar(CLASES[0], [canal(**{"P.VENTA": precio})])

    def test_rechaza_campos_que_desplazan_la_trama(self):
        for cliente in (" ", "CLIENTE_DEMASIADO_LARGO"):
            for clase in CLASES:
                with self.assertRaisesRegex(ValueError, "NIT CLIENTE"):
                    preparar(clase, [canal(**{"NIT CLIENTE ": cliente})])
        for sucursal in (None, "", "0001"):
            with self.assertRaisesRegex(ValueError, "SUCURSAL"):
                preparar(CLASES[0], [canal(**{"SUCURSAL": sucursal})])
        for fecha in (None, "", "20261301"):
            for clase in CLASES:
                with self.assertRaisesRegex(ValueError, "FECHA SACRIFICIO"):
                    preparar(clase, [canal(**{"FECHA SACRIFICIO SIESA": fecha})])

    def test_rechaza_canales_de_otra_empresa_aunque_la_primera_fila_coincida(self):
        for clase in CLASES:
            with self.assertRaisesRegex(ValueError, "seleccionaste"):
                preparar(clase, [canal(), canal("28746-474", CIA=4)])

    def test_rechaza_hoja_canal_vacia_sin_indexerror(self):
        for clase in CLASES:
            with self.assertRaisesRegex(ValueError, "CANAL no tiene datos"):
                preparar(clase, [])

    def test_rechaza_tipo_sin_referencia(self):
        for clase in CLASES:
            with self.assertRaisesRegex(ValueError, "referencia Siesa"):
                preparar(clase, [canal(tipo="DESCONOCIDO")])

    def test_rechaza_archivo_sin_pedidos_o_sin_fecha_coincidente(self):
        for cambios, mensaje in (
            ({"NIT CLIENTE ": None}, "no tiene canales con pedido"),
            ({"REMISION": None}, "no tiene canales con pedido"),
            ({"FECHA PEDIDO SIESA": "20261030", "FECHA SACRIFICIO SIESA": "20261030"},
             "No hay canales con pedido"),
        ):
            for clase in CLASES:
                with self.subTest(cambios=cambios, clase=clase.__name__):
                    with self.assertRaisesRegex(ValueError, mensaje):
                        preparar(clase, [canal(**cambios)])

    def test_envio_por_lotes_conserva_identidad_y_no_parte_remisiones(self):
        filas = [
            canal("28746-480", 20),
            canal("28746-475", 10, "VACA"),
            canal("28746-479", 20, "VACA"),
            canal("28746-473", 10),
            canal("28746-476", 10, "VACA"),
        ]
        salidas = []
        for modulo in (doc_pedidos, compromisos_pedidos):
            envios = []

            def capturar(xml_path):
                lineas = Path(xml_path).with_suffix(".txt").read_text(encoding="utf-8").splitlines()
                envios.append(lineas)
                return {"ok": True, "mensaje": "Prueba local", "error": False}

            with tempfile.TemporaryDirectory() as work_dir:
                with patch.object(pd, "read_excel", return_value=REFERENCIAS.copy()), \
                     patch.object(siesa, "LOTE_LINEAS", 2), \
                     patch.object(siesa, "consumir_servicio_web", side_effect=capturar):
                    resultado = modulo.procesar(
                        None, work_dir, "3", FECHA, parametros={}, datos=filas,
                    )
                self.assertTrue(resultado["ok"])
                self.assertEqual(len(envios), 2)
                remisiones_vistas = set()
                for lote in envios:
                    self.assertEqual([int(r[:7]) for r in lote], list(range(1, len(lote) + 1)))
                    remisiones = {int(r[27:35] if r[7:11] == "0430" else r[24:32])
                                  for r in lote[1:-1]}
                    self.assertTrue(remisiones.isdisjoint(remisiones_vistas))
                    remisiones_vistas.update(remisiones)
                salidas.append([r for lote in envios for r in lote])
        self.comprobar_correspondencia(salidas[0], salidas[1], filas)


class ArchivoAnalisisTests(CorrespondenciaMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archivo = os.path.join(siesa.RUTA_PROYECTO, "ANALISIS.xlsx")
        if not os.path.exists(cls.archivo):
            raise unittest.SkipTest("No se encuentra el archivo de ejemplo ANALISIS.xlsx.")
        cls.datos = siesa.leer_datos_canal(None, cls.archivo, skiprows=6)

    def test_archivo_real_sin_cliente_no_se_envia(self):
        if self.datos["NIT CLIENTE "].notna().any():
            self.skipTest("El archivo de ejemplo ahora contiene clientes.")
        for modulo in (doc_pedidos, compromisos_pedidos):
            with tempfile.TemporaryDirectory() as work_dir:
                with patch.object(siesa, "consumir_servicio_web") as servicio:
                    with self.assertRaisesRegex(ValueError, "no tiene canales con pedido"):
                        modulo.procesar(self.archivo, work_dir, "3", FECHA)
                    servicio.assert_not_called()

    def test_lotes_del_archivo_real_con_pedido_simulado_sin_modificar_excel(self):
        datos = self.datos[self.datos["LOTE"].notna()].copy()
        self.assertGreater(len(datos), 0)
        datos["NIT CLIENTE "] = "CLIENTE_PRUEBA"
        datos["SUCURSAL"] = "001"
        datos["P.VENTA"] = 10000
        datos["FECHA PEDIDO SIESA"] = FECHA
        filas = datos.to_dict("records")
        salidas = []
        with tempfile.TemporaryDirectory() as work_dir:
            archivo_prueba = os.path.join(work_dir, "analisis_prueba.xlsx")
            datos.to_excel(archivo_prueba, sheet_name="CANAL", startrow=6, index=False)
            for modulo, nombre in (
                (doc_pedidos, "PedidoVentaCanal.txt"),
                (compromisos_pedidos, "Compromiso_PedidoVentaCanal.txt"),
            ):
                with patch.object(siesa, "consumir_servicio_web",
                                  return_value={"ok": True, "mensaje": "Prueba local"}):
                    resultado = modulo.procesar(archivo_prueba, work_dir, "3", FECHA)
                self.assertTrue(resultado["ok"])
                salidas.append(Path(work_dir, nombre).read_text(encoding="utf-8").splitlines())
        self.comprobar_correspondencia(salidas[0], salidas[1], filas)


if __name__ == "__main__":
    unittest.main()

import unittest

from procesadores.taller_calculos import calcular


class TallerCalculosTests(unittest.TestCase):
    def test_formulas_excel_y_distribucion(self):
        resultado = calcular(
            [{"cantidad": 100, "costo_promedio": 11200}],
            [{"cantidad": 80, "precio_venta": 20000}, {"cantidad": 15, "precio_venta": 4000}],
        )
        self.assertEqual(resultado["costo_total"], 1120000)
        self.assertEqual(resultado["venta_total"], 1660000)
        self.assertEqual(resultado["utilidad"], 540000)
        self.assertEqual(resultado["merma"], 5)
        self.assertAlmostEqual(resultado["margen"], 540000 / 1660000)
        self.assertEqual(resultado["productos"][0]["participacion"], .8)
        self.assertEqual(resultado["productos"][0]["costo_unitario"], 13493.98)

    def test_varios_insumos_y_subproducto_sin_precio(self):
        resultado = calcular(
            [{"cantidad": 2, "costo_promedio": 100}, {"cantidad": 3, "costo_promedio": 200}],
            [{"cantidad": 4, "precio_venta": 250}, {"cantidad": 1, "precio_venta": 0}],
        )
        self.assertEqual(resultado["costo_total"], 800)
        self.assertEqual(resultado["productos"][1]["costo_unitario"], 0)

    def test_rechaza_numeros_invalidos_y_venta_cero(self):
        for cantidad in (0, -1, "NaN", "Infinity", "texto"):
            with self.subTest(cantidad=cantidad), self.assertRaises(ValueError):
                calcular([{"cantidad": cantidad, "costo_promedio": 1}],
                         [{"cantidad": 1, "precio_venta": 1}])
        with self.assertRaisesRegex(ValueError, "venta"):
            calcular([{"cantidad": 1, "costo_promedio": 1}],
                     [{"cantidad": 1, "precio_venta": 0}])

    def test_no_suma_unidades_incomparables(self):
        with self.assertRaisesRegex(ValueError, "misma UM"):
            calcular([{"cantidad": 10, "costo_promedio": 100, "um": "kg"}],
                     [{"cantidad": 1, "precio_venta": 2000, "um": "und"}])


if __name__ == "__main__":
    unittest.main()
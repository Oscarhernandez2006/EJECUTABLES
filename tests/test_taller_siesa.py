import copy
import io
import os
import unittest
from unittest.mock import patch, Mock
from xml.etree import ElementTree as ET

import openpyxl

from app import app
from procesadores import taller_siesa


def consulta(recurso, filtros):
    if recurso == "detalle":
        return {"codigo": filtros["item"], "referencia": "000123", "descripcion": "Pechuga",
                "um": "kg", "existencia": 100, "costo_promedio": 11200, "precio_venta": 20000}
    return [{"codigo": {"centros": "407", "bodegas": "40702", "listas": "01"}[recurso],
             "descripcion": "Principal"}]


def captura():
    return {"empresa": "4", "fecha": "20261123", "co": "407", "lista": "01", "talleres": [
        {"numero": 1, "insumos": [{"item": "4049", "bodega": "40702", "cantidad": 100,
                                    "costo_promedio": 1}],
         "productos": [{"item": "4025", "bodega": "40702", "cantidad": 95, "precio_venta": 21000}]}]}


def captura_fria():
    payload = captura()
    payload.update(empresa="8", co="801", lista="001")
    for grupo in ("insumos", "productos"):
        for fila in payload["talleres"][0][grupo]:
            fila.update(item="52" if grupo == "insumos" else "53", bodega="80101", lote="315-19-26")
    return payload


def consulta_fria(recurso, filtros):
    if recurso == "lotes":
        return {"maneja_lote": True, "data": [{"codigo": "315-19-26", "descripcion": "Lote activo"}]}
    if recurso == "detalle":
        return {"codigo": filtros["item"], "referencia": "6309", "descripcion": "Salchichon",
                "um": "U", "existencia": 326, "costo_promedio": 2580.44, "precio_venta": 5341,
                "tiene_costo": filtros["item"] == "52", "tiene_precio": True, "incluye_impuestos": False}
    return [{"codigo": {"centros": "801", "bodegas": "80101", "listas": "001"}[recurso],
             "descripcion": "Principal"}]


class TallerSiesaTests(unittest.TestCase):
    def test_rest_usa_base_url_y_timeout_ms_sin_duplicar_prefijo(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {"empresa": 8, "data": [{"codigo": "801", "descripcion": "MALAMBO"}]}
        for base in ("https://consulta.example", "https://consulta.example/carnes-frias/"):
            with self.subTest(base=base), patch.dict(os.environ, {
                "SIESA_CONSULTAS_BASE_URL": base, "SIESA_CONSULTAS_API_KEY": "prueba",
                "SIESA_CONSULTAS_TIMEOUT_MS": "30000",
            }, clear=True), patch.object(taller_siesa.requests, "get", return_value=respuesta) as get:
                taller_siesa.consultar("centros", {"empresa": "8", "fecha": "20261123"})
                self.assertEqual(get.call_args.args[0], "https://consulta.example/carnes-frias/centros-operacion")
                self.assertEqual(get.call_args.kwargs["timeout"], (5, 30))

    def test_rest_rechaza_timeout_invalido_y_urls_inseguras(self):
        for timeout in ("0", "-1", "abc", "300001"):
            with self.subTest(timeout=timeout), patch.dict(os.environ, {"SIESA_CONSULTAS_TIMEOUT_MS": timeout}), \
                 self.assertRaises(taller_siesa.ConsultaNoDisponible):
                taller_siesa.conexion_rest()
        for base in ("http://consulta.example", "https://usuario:clave@consulta.example", "https://consulta.example?token=secreto"):
            with self.subTest(base=base), patch.dict(os.environ, {"SIESA_CONSULTAS_BASE_URL": base}), \
                 self.assertRaises(taller_siesa.ConsultaNoDisponible):
                taller_siesa.conexion_rest()

    def test_configuracion_por_compania_no_expone_clave(self):
        with app.test_client() as cliente, patch.dict(os.environ, {"SIESA_CONSULTAS_API_KEY": "secreto-de-prueba"}, clear=True):
            respuesta = cliente.get("/api/taller/configuracion?empresa=8")
            self.assertTrue(respuesta.get_json()["disponible"])
            self.assertTrue(respuesta.get_json()["solo_hoy"])
            self.assertEqual(respuesta.get_json()["proveedor"], "rest")
            self.assertNotIn("secreto-de-prueba", respuesta.get_data(as_text=True))
            self.assertFalse(cliente.get("/api/taller/configuracion?empresa=4").get_json()["disponible"])

    @patch.object(taller_siesa, "fecha_hoy", return_value="20261123")
    @patch.object(taller_siesa, "consultar", side_effect=consulta_fria)
    def test_captura_fria_permite_terminado_sin_costo_y_exige_lote(self, consultar, hoy):
        payload = captura_fria()
        hojas, _, _ = taller_siesa.preparar_captura(payload)
        self.assertEqual(hojas["Hoja1"][0]["COSTO UNITARIO"], 2580.44)
        for lote in ("", "inexistente"):
            payload["talleres"][0]["insumos"][0]["lote"] = lote
            with self.assertRaisesRegex(ValueError, "lote activo"):
                taller_siesa.preparar_captura(payload)

    @patch.object(taller_siesa, "fecha_hoy", return_value="20261123")
    def test_captura_fria_rechaza_costo_ausente_pero_no_cero_real(self, hoy):
        def simular(recurso, filtros):
            datos = consulta_fria(recurso, filtros)
            if recurso == "detalle":
                datos.update(costo_promedio=0, tiene_costo=False)
            return datos
        with patch.object(taller_siesa, "consultar", side_effect=simular):
            with self.assertRaisesRegex(ValueError, "no tiene costo"):
                taller_siesa.preparar_captura(captura_fria())
        def cero_real(recurso, filtros):
            datos = simular(recurso, filtros)
            if recurso == "detalle":
                datos["tiene_costo"] = True
            return datos
        with patch.object(taller_siesa, "consultar", side_effect=cero_real):
            _, _, resumen = taller_siesa.preparar_captura(captura_fria())
            self.assertEqual(resumen["costo_total"], 0)

    @patch.object(taller_siesa, "fecha_hoy", return_value="20261123")
    def test_precio_ausente_requiere_edicion_explicita(self, hoy):
        def simular(recurso, filtros):
            datos = consulta_fria(recurso, filtros)
            if recurso == "detalle":
                datos.update(precio_venta=0, tiene_precio=False)
            return datos
        with patch.object(taller_siesa, "consultar", side_effect=simular):
            payload = captura_fria()
            with self.assertRaisesRegex(ValueError, "Ingresa explícitamente"):
                taller_siesa.preparar_captura(payload)
            payload["talleres"][0]["productos"][0]["precio_editado"] = True
            _, _, resumen = taller_siesa.preparar_captura(payload)
            self.assertEqual(resumen["venta_total"], 1995000)

    def test_rest_traduce_errores_y_rechaza_datos_ambiguos(self):
        with patch.dict(os.environ, {"SIESA_CONSULTAS_API_KEY": "prueba"}):
            respuesta = Mock(status_code=400)
            respuesta.json.return_value = {"detail": "La bodega no pertenece al centro"}
            with patch.object(taller_siesa.requests, "get", return_value=respuesta):
                with self.assertRaisesRegex(ValueError, "no pertenece"):
                    taller_siesa.consultar("bodegas", {"empresa": "8", "fecha": "20261123", "co": "801"})
            respuesta.status_code = 200
            respuesta.json.return_value = {"data": {"codigo": "801"}}
            with patch.object(taller_siesa.requests, "get", return_value=respuesta):
                with self.assertRaises(taller_siesa.ConsultaNoDisponible):
                    taller_siesa.consultar("centros", {"empresa": "8", "fecha": "20261123"})

    def test_rest_envia_clave_solo_en_cabecera_y_desenvuelve_catalogo(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {"empresa": 8, "total": 1,
                                       "data": [{"codigo": "801", "descripcion": "MALAMBO"}]}
        with patch.dict(os.environ, {"SIESA_CONSULTAS_API_KEY": "clave-de-prueba"}), \
             patch.object(taller_siesa.requests, "get", return_value=respuesta) as get:
            filas = taller_siesa.consultar("centros", {"empresa": "8", "fecha": "20261123", "q": "mal"})
            self.assertEqual(filas[0]["codigo"], "801")
            self.assertTrue(get.call_args.args[0].endswith("/carnes-frias/centros-operacion"))
            self.assertEqual(get.call_args.kwargs["headers"]["X-API-Key"], "clave-de-prueba")
            self.assertNotIn("clave", get.call_args.kwargs["params"])
            self.assertFalse(get.call_args.kwargs["allow_redirects"])

    def test_rest_conserva_indicadores_para_no_inventar_costo(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {
            "codigo": "52", "referencia": "6309", "descripcion": "Salchichon", "um": "U",
            "existencia": 326, "costo_promedio": 0, "precio_venta": 5341,
            "tiene_costo": False, "tiene_precio": True, "incluye_impuestos": False,
            "um_precio": "U", "fecha_corte": "20261123", "avisos": ["Sin costo"],
        }
        with patch.dict(os.environ, {"SIESA_CONSULTAS_API_KEY": "prueba"}), \
             patch.object(taller_siesa, "fecha_hoy", return_value="20261123"), \
             patch.object(taller_siesa.requests, "get", return_value=respuesta):
            detalle = taller_siesa.consultar("detalle", {"empresa": "8", "fecha": "20261123", "item": "52"})
            self.assertFalse(detalle["tiene_costo"])
            self.assertEqual(detalle["costo_promedio"], 0)
            with self.assertRaisesRegex(ValueError, "hoy"):
                taller_siesa.consultar("detalle", {"empresa": "8", "fecha": "20261122", "item": "52"})

    def test_rest_autenticacion_no_expone_respuesta_ni_clave(self):
        with patch.dict(os.environ, {"SIESA_CONSULTAS_API_KEY": "no-mostrar"}), \
             patch.object(taller_siesa.requests, "get", return_value=Mock(status_code=401)):
            with self.assertRaises(taller_siesa.ConsultaNoDisponible) as resultado:
                taller_siesa.consultar("centros", {"empresa": "8", "fecha": "20261123"})
            self.assertNotIn("no-mostrar", str(resultado.exception))

    def test_rest_lotes_de_destino_incluyen_lotes_sin_existencia(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {"maneja_lote": True, "data": [{"codigo": "315-19-26", "descripcion": "Lote activo"}]}
        with patch.dict(os.environ, {"SIESA_CONSULTAS_API_KEY": "prueba"}), \
             patch.object(taller_siesa.requests, "get", return_value=respuesta) as get:
            lotes = taller_siesa.consultar("lotes", {
                "empresa": "8", "fecha": "20261123", "item": "52", "bodega": "80101", "solo_con_existencia": "false"})
            self.assertTrue(lotes["maneja_lote"])
            self.assertEqual(get.call_args.kwargs["params"]["solo_con_existencia"], "false")

    @patch.object(taller_siesa, "consultar", side_effect=consulta)
    def test_costo_cliente_se_ignora_y_precio_se_puede_editar(self, consultar):
        hojas, _, resumen = taller_siesa.preparar_captura(captura())
        self.assertEqual(hojas["Hoja1"][0]["COSTO UNITARIO"], 11200)
        self.assertEqual(resumen["costo_total"], 1120000)
        self.assertEqual(resumen["venta_total"], 1995000)
        self.assertEqual(resumen["talleres"][0]["merma"], 5)

    @patch.object(taller_siesa, "consultar", side_effect=consulta)
    def test_existencia_se_acumula_entre_transformaciones(self, consultar):
        payload = captura()
        adicional = copy.deepcopy(payload["talleres"][0])
        adicional["numero"] = 2
        payload["talleres"].append(adicional)
        with self.assertRaisesRegex(ValueError, "Existencia insuficiente"):
            taller_siesa.preparar_captura(payload)

    @patch.object(taller_siesa, "consultar", side_effect=consulta)
    def test_validar_no_importa_documentos(self, consultar):
        with app.test_client() as cliente, patch("procesadores.siesa.consumir_servicio_web") as importar:
            respuesta = cliente.post("/api/taller/validar", json=captura())
            self.assertEqual(respuesta.status_code, 200)
            importar.assert_not_called()

    def test_contexto_invalido_y_conexion_sin_configurar(self):
        with app.test_client() as cliente:
            self.assertEqual(cliente.post("/api/taller/validar", json=[]).status_code, 400)
            self.assertEqual(cliente.get("/api/taller/catalogo/detalle?empresa=4&fecha=20260230").status_code, 400)
            with patch.dict(os.environ, {}, clear=True):
                respuesta = cliente.get("/api/taller/catalogo/centros?empresa=4&fecha=20261123")
                self.assertEqual(respuesta.status_code, 503)

    @patch.object(taller_siesa, "consultar", side_effect=consulta)
    def test_exportar_libro_reimportable_sin_ejecutar_siesa(self, consultar):
        with app.test_client() as cliente, patch("procesadores.siesa.consumir_servicio_web") as importar:
            respuesta = cliente.post("/api/taller/exportar", json=captura())
            self.assertEqual(respuesta.status_code, 200)
            libro = openpyxl.load_workbook(io.BytesIO(respuesta.data), data_only=True)
            self.assertEqual(libro.sheetnames, ["Hoja1", "TALLER", "CONSOLIDADO", "BD"])
            self.assertEqual(libro["Hoja1"]["N2"].value, 11200)
            self.assertEqual(libro["CONSOLIDADO"]["G2"].value, 1120000)
            libro.close()
            importar.assert_not_called()

    @patch.object(taller_siesa, "consultar", side_effect=consulta)
    def test_subproducto_sin_precio_es_valido_si_hay_venta(self, consultar):
        payload = captura()
        payload["talleres"][0]["productos"].append(
            {"item": "4063", "bodega": "40702", "cantidad": 1, "precio_venta": 0})
        _, _, resumen = taller_siesa.preparar_captura(payload)
        self.assertEqual(resumen["talleres"][0]["productos"][1]["costo_unitario"], 0)

    @patch.object(taller_siesa, "consultar", side_effect=consulta)
    def test_cambio_despues_de_confirmar_no_importa(self, consultar):
        with app.test_client() as cliente, patch("procesadores.siesa.consumir_servicio_web") as importar:
            payload = captura()
            validacion = cliente.post("/api/taller/validar", json=payload).get_json()
            payload["revision"] = validacion["revision"]
            payload["talleres"][0]["productos"][0]["precio_venta"] = 22000
            respuesta = cliente.post("/api/taller/ejecutar", json=payload)
            self.assertEqual(respuesta.status_code, 409)
            importar.assert_not_called()

    @patch.object(taller_siesa, "consultar", side_effect=consulta)
    def test_importa_captura_confirmada_con_costo_del_servidor(self, consultar):
        with app.test_client() as cliente, patch("procesadores.siesa.consumir_servicio_web", return_value={"ok": True}) as importar:
            payload = captura()
            payload["revision"] = cliente.post("/api/taller/validar", json=payload).get_json()["revision"]
            respuesta = cliente.post("/api/taller/ejecutar", json=payload)
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.get_json()["ok"])
            importar.assert_called_once()

    def test_soap_escapa_parametros_y_lee_dataset(self):
        plantilla = "<Consulta><Texto>{q}</Texto></Consulta>"
        respuesta = Mock(content=b'<Envelope><Table><codigo>4049</codigo><descripcion>Pollo</descripcion>'
                                 b'<referencia>4049</referencia><um>kg</um></Table></Envelope>')
        with patch.dict(os.environ, {"SIESA_TALLER_XML_PRODUCTOS": plantilla}), \
             patch.object(taller_siesa.requests, "post", return_value=respuesta) as post:
            filas = taller_siesa.consultar("productos", {"empresa": "4", "fecha": "20261123", "q": "A&B<>"})
            self.assertEqual(filas[0]["codigo"], "4049")
            sobre = ET.fromstring(post.call_args.kwargs["data"])
            parametro = next(nodo for nodo in sobre.iter() if nodo.tag.endswith("pvstrxmlParametros"))
            self.assertEqual(ET.fromstring(parametro.text).findtext("Texto"), "A&B<>")


if __name__ == "__main__":
    unittest.main()
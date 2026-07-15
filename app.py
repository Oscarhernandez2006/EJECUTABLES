"""Aplicación web para la carga y ejecución de procesos de integración con Siesa.

Expone una interfaz donde el usuario selecciona el tipo de proceso
(Pedidos, Requisiciones o Sobrecostos), carga el archivo Excel y ejecuta
la importación hacia el servicio web de Siesa.

Diseñado para integrarse posteriormente a un hub de aplicaciones.
"""

import os
import tempfile
import traceback

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from procesadores import PROCESADORES

app = Flask(__name__)

# Carpeta base del proyecto (donde viven las plantillas Excel).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Límite de tamaño de archivo: 25 MB.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

# Extensiones de Excel permitidas.
EXTENSIONES_PERMITIDAS = {".xlsx", ".xlsm", ".xls"}

# Metadatos de cada proceso para renderizar la interfaz.
PROCESOS = [
    {
        "id": "pedidos",
        "nombre": "Pedidos",
        "descripcion": "Importa pedidos de venta a Siesa.",
        "hoja": "PEDIDO",
        "archivo": "PEDIDOS-SOBRECOSTOS.xlsx",
    },
    {
        "id": "requisiciones",
        "nombre": "Requisiciones",
        "descripcion": "Importa transferencias / requisiciones de inventario.",
        "hoja": "TRASNFERENCIA",
        "archivo": "PEDIDOS-SOBRECOSTOS.xlsx",
    },
    {
        "id": "sobrecostos",
        "nombre": "Sobrecostos",
        "descripcion": "Importa ajustes de sobrecostos a documentos base.",
        "hoja": "SOBRECOSTOS",
        "archivo": "PEDIDOS-SOBRECOSTOS.xlsx",
    },
    {
        "id": "cruce_contable",
        "nombre": "Cruce Contable",
        "descripcion": "Genera el asiento contable (débito/crédito) de reclasificación de compra.",
        "hoja": "CANAL",
        "archivo": "ANALISIS.xlsx",
    },
]


def _extension_valida(nombre_archivo):
    _, ext = os.path.splitext(nombre_archivo.lower())
    return ext in EXTENSIONES_PERMITIDAS


@app.route("/")
def index():
    return render_template("index.html", procesos=PROCESOS)


@app.route("/plantilla/<tipo>")
def descargar_plantilla(tipo):
    """Descarga el archivo Excel de plantilla del proceso indicado."""
    proceso = next((p for p in PROCESOS if p["id"] == tipo), None)
    if proceso is None:
        abort(404)
    archivo = proceso["archivo"]
    if not os.path.exists(os.path.join(BASE_DIR, archivo)):
        abort(404)
    return send_from_directory(BASE_DIR, archivo, as_attachment=True)


def _mensaje_amigable(exc):
    """Traduce las excepciones más comunes a un mensaje claro para el usuario."""
    texto = str(exc)
    tipo = type(exc).__name__

    if isinstance(exc, KeyError):
        return f"Falta la columna {texto} en el Excel (revisa el encabezado de la hoja)."
    if isinstance(exc, ValueError) and "Worksheet" in texto:
        return f"No se encontró la hoja indicada en el Excel: {texto}."
    if isinstance(exc, IndexError):
        return ("Faltan parámetros en la hoja PARAMETROS (se esperaban más filas en "
                "la columna CODIGO_PARAMETRO).")
    if isinstance(exc, FileNotFoundError):
        return "No se pudo leer el archivo. Vuelve a subirlo."
    return f"{tipo}: {texto}"


def _ejecutar_proceso(modulo, tipo, excel_path):
    """Ejecuta un procesador sobre un Excel y devuelve la respuesta JSON de Flask."""
    with tempfile.TemporaryDirectory(prefix="siesa_") as work_dir:
        try:
            resultado = modulo.procesar(excel_path, work_dir)
        except Exception as exc:  # noqa: BLE001 - se reporta al usuario
            detalle = traceback.format_exc()
            app.logger.error("Error procesando %s: %s", tipo, detalle)
            return jsonify({
                "ok": False,
                "mensaje": _mensaje_amigable(exc),
                "tipo_error": type(exc).__name__,
                "detalle": detalle,
            }), 500

    exito = resultado.get("ok", False)
    return jsonify({
        "ok": exito,
        "mensaje": "Proceso ejecutado correctamente." if exito
        else f"El servicio respondió con código {resultado.get('status_code')}.",
        "status_code": resultado.get("status_code"),
        "registros": resultado.get("registros"),
        "respuesta": resultado.get("respuesta"),
    }), (200 if exito else 502)


@app.route("/api/procesar/<tipo>", methods=["POST"])
def procesar(tipo):
    modulo = PROCESADORES.get(tipo)
    if modulo is None:
        return jsonify({"ok": False, "mensaje": f"Proceso no válido: {tipo}"}), 404

    if "archivo" not in request.files:
        return jsonify({"ok": False, "mensaje": "No se recibió ningún archivo."}), 400

    archivo = request.files["archivo"]
    if not archivo.filename:
        return jsonify({"ok": False, "mensaje": "No se seleccionó ningún archivo."}), 400

    if not _extension_valida(archivo.filename):
        return jsonify({
            "ok": False,
            "mensaje": "Formato no permitido. Sube un archivo Excel (.xlsx, .xlsm, .xls).",
        }), 400

    nombre_seguro = secure_filename(archivo.filename)

    with tempfile.TemporaryDirectory(prefix="siesa_upload_") as up_dir:
        excel_path = os.path.join(up_dir, nombre_seguro)
        archivo.save(excel_path)
        return _ejecutar_proceso(modulo, tipo, excel_path)


@app.errorhandler(413)
def archivo_muy_grande(_error):
    return jsonify({"ok": False, "mensaje": "El archivo supera el tamaño máximo permitido (25 MB)."}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

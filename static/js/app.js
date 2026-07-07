// Estado de la aplicación
const state = {
    proceso: null,
    archivo: null,
};

// Referencias del DOM
const navItems = document.querySelectorAll(".nav__item");
const tituloProceso = document.getElementById("tituloProceso");
const descProceso = document.getElementById("descProceso");
const hojaBadge = document.getElementById("hojaBadge");

const dropzone = document.getElementById("dropzone");
const inputArchivo = document.getElementById("inputArchivo");
const fileInfo = document.getElementById("fileInfo");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const btnQuitar = document.getElementById("btnQuitar");
const btnEjecutar = document.getElementById("btnEjecutar");

const resultCard = document.getElementById("resultCard");
const resultStatus = document.getElementById("resultStatus");
const resultMeta = document.getElementById("resultMeta");
const resultMessage = document.getElementById("resultMessage");
const resultDetails = document.getElementById("resultDetails");
const resultRaw = document.getElementById("resultRaw");

const EXTENSIONES = [".xlsx", ".xlsm", ".xls"];

// ---------- Navegación entre procesos ----------
function seleccionarProceso(item) {
    navItems.forEach((n) => n.classList.remove("is-active"));
    item.classList.add("is-active");

    state.proceso = {
        id: item.dataset.proceso,
        nombre: item.dataset.nombre,
        descripcion: item.dataset.descripcion,
        hoja: item.dataset.hoja,
    };

    tituloProceso.textContent = state.proceso.nombre;
    descProceso.textContent = state.proceso.descripcion;
    hojaBadge.textContent = `Hoja: ${state.proceso.hoja}`;

    ocultarResultado();
}

navItems.forEach((item) => {
    item.addEventListener("click", () => seleccionarProceso(item));
});

// Inicializa con el primer proceso activo
const primerItem = document.querySelector(".nav__item.is-active") || navItems[0];
if (primerItem) seleccionarProceso(primerItem);

// ---------- Manejo de archivo ----------
function extensionValida(nombre) {
    const lower = nombre.toLowerCase();
    return EXTENSIONES.some((ext) => lower.endsWith(ext));
}

function formatearTamano(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function establecerArchivo(archivo) {
    if (!archivo) return;

    if (!extensionValida(archivo.name)) {
        mostrarResultado(false, "Formato no permitido", "Selecciona un archivo Excel (.xlsx, .xlsm, .xls).");
        return;
    }

    state.archivo = archivo;
    fileName.textContent = archivo.name;
    fileSize.textContent = formatearTamano(archivo.size);
    fileInfo.hidden = false;
    btnEjecutar.disabled = false;
    ocultarResultado();
}

function quitarArchivo() {
    state.archivo = null;
    inputArchivo.value = "";
    fileInfo.hidden = true;
    btnEjecutar.disabled = true;
}

inputArchivo.addEventListener("change", (e) => {
    establecerArchivo(e.target.files[0]);
});

btnQuitar.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    quitarArchivo();
});

// Drag & drop
["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropzone.classList.add("is-dragover");
    });
});

["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropzone.classList.remove("is-dragover");
    });
});

dropzone.addEventListener("drop", (e) => {
    const archivo = e.dataTransfer.files[0];
    establecerArchivo(archivo);
});

// ---------- Resultado ----------
function ocultarResultado() {
    resultCard.hidden = true;
    resultDetails.hidden = true;
    resultCard.classList.remove("is-success", "is-error");
}

function mostrarResultado(exito, titulo, mensaje, meta = "", respuesta = "", opciones = {}) {
    resultCard.hidden = false;
    resultCard.classList.remove("is-success", "is-error");
    resultCard.classList.add(exito ? "is-success" : "is-error");

    resultStatus.textContent = titulo;
    resultMeta.textContent = meta;
    resultMessage.textContent = mensaje;

    const summary = resultDetails.querySelector("summary");
    if (summary) {
        summary.textContent = opciones.etiquetaDetalle || "Ver respuesta del servicio";
    }

    if (respuesta) {
        resultRaw.textContent = respuesta;
        resultDetails.hidden = false;
        resultDetails.open = Boolean(opciones.abrirDetalle);
    } else {
        resultDetails.hidden = true;
    }

    resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---------- Ejecución ----------
function setCargando(cargando) {
    const label = btnEjecutar.querySelector(".btn__label");
    const spinner = btnEjecutar.querySelector(".btn__spinner");
    btnEjecutar.disabled = cargando || !state.archivo;
    spinner.hidden = !cargando;
    label.textContent = cargando ? "Procesando…" : "Ejecutar proceso";
}

async function llamarProceso(url, formData) {
    setCargando(true);
    ocultarResultado();

    try {
        const opciones = { method: "POST" };
        if (formData) opciones.body = formData;

        const resp = await fetch(url, opciones);
        const data = await resp.json();

        const meta = data.registros != null ? `${data.registros} registro(s)` : "";
        if (data.ok) {
            mostrarResultado(true, "Proceso exitoso", data.mensaje || "Ejecutado correctamente.", meta, data.respuesta || "", {
                etiquetaDetalle: "Ver respuesta del servicio",
            });
        } else {
            // En errores mostramos el detalle/traceback de Python para poder corregir la plantilla.
            const detalle = data.detalle || data.respuesta || "";
            const titulo = data.tipo_error ? `Error: ${data.tipo_error}` : "Proceso con errores";
            mostrarResultado(false, titulo, data.mensaje || "Ocurrió un error.", meta, detalle, {
                etiquetaDetalle: "Ver detalle técnico (Python)",
                abrirDetalle: Boolean(data.detalle),
            });
        }
    } catch (err) {
        mostrarResultado(false, "Error de conexión", "No se pudo comunicar con el servidor. Intenta nuevamente.");
    } finally {
        setCargando(false);
    }
}

function ejecutar() {
    if (!state.archivo || !state.proceso) return;
    const formData = new FormData();
    formData.append("archivo", state.archivo);
    llamarProceso(`/api/procesar/${state.proceso.id}`, formData);
}

btnEjecutar.addEventListener("click", ejecutar);

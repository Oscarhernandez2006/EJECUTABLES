// Estado de la aplicación
const state = {
    proceso: null,
    archivos: {}, // clave de entrada -> File seleccionado
};

// Configuración de procesos inyectada por el servidor (incluye las "entradas").
const PROCESOS = window.PROCESOS || [];

// Referencias del DOM
const navItems = document.querySelectorAll(".nav__item");
const tituloProceso = document.getElementById("tituloProceso");
const descProceso = document.getElementById("descProceso");
const hojaBadge = document.getElementById("hojaBadge");

const entradasContainer = document.getElementById("entradas");
const entradaTemplate = document.getElementById("entradaTemplate");
const btnEjecutar = document.getElementById("btnEjecutar");

const resultCard = document.getElementById("resultCard");
const resultStatus = document.getElementById("resultStatus");
const resultMeta = document.getElementById("resultMeta");
const resultMessage = document.getElementById("resultMessage");
const resultDetails = document.getElementById("resultDetails");
const resultRaw = document.getElementById("resultRaw");

const EXTENSIONES = [".xlsx", ".xlsm", ".xls"];

function procesoPorId(id) {
    return PROCESOS.find((p) => p.id === id) || null;
}

// ---------- Utilidades de archivo ----------
function extensionValida(nombre) {
    const lower = nombre.toLowerCase();
    return EXTENSIONES.some((ext) => lower.endsWith(ext));
}

function formatearTamano(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

// ---------- Render de las zonas de carga ----------
function renderEntradas(proceso) {
    entradasContainer.innerHTML = "";
    state.archivos = {};

    proceso.entradas.forEach((entrada) => {
        const nodo = entradaTemplate.content.firstElementChild.cloneNode(true);
        nodo.dataset.clave = entrada.clave;

        nodo.querySelector(".entrada__label").textContent = entrada.etiqueta;

        const plantilla = nodo.querySelector(".entrada__plantilla");
        plantilla.href = `/plantilla/${proceso.id}/${entrada.clave}`;

        const dropzone = nodo.querySelector(".dropzone");
        const input = nodo.querySelector(".entrada__input");
        const fileInfo = nodo.querySelector(".file-info");
        const fileName = nodo.querySelector(".file-info__name");
        const fileSize = nodo.querySelector(".file-info__size");
        const btnQuitar = nodo.querySelector(".file-info__remove");
        const subtitulo = nodo.querySelector(".dropzone__sub");

        // Deja claro qué archivo se espera en esta zona.
        subtitulo.textContent = `Archivo esperado: ${entrada.archivo}`;

        const establecer = (archivo) => {
            if (!archivo) return;
            if (!extensionValida(archivo.name)) {
                mostrarResultado(false, "Formato no permitido", `'${entrada.etiqueta}': selecciona un Excel (.xlsx, .xlsm, .xls).`);
                return;
            }
            state.archivos[entrada.clave] = archivo;
            fileName.textContent = archivo.name;
            fileSize.textContent = formatearTamano(archivo.size);
            fileInfo.hidden = false;
            ocultarResultado();
            actualizarBotonEjecutar();
        };

        const quitar = () => {
            delete state.archivos[entrada.clave];
            input.value = "";
            fileInfo.hidden = true;
            actualizarBotonEjecutar();
        };

        input.addEventListener("change", (e) => establecer(e.target.files[0]));

        btnQuitar.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            quitar();
        });

        // Drag & drop por zona
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
        dropzone.addEventListener("drop", (e) => establecer(e.dataTransfer.files[0]));

        entradasContainer.appendChild(nodo);
    });
}

function archivosCompletos() {
    if (!state.proceso) return false;
    return state.proceso.entradas.every((e) => Boolean(state.archivos[e.clave]));
}

function actualizarBotonEjecutar() {
    btnEjecutar.disabled = !archivosCompletos();
}

// ---------- Navegación entre procesos ----------
function seleccionarProceso(item) {
    navItems.forEach((n) => n.classList.remove("is-active"));
    item.classList.add("is-active");

    const proceso = procesoPorId(item.dataset.proceso);
    state.proceso = proceso;

    tituloProceso.textContent = proceso.nombre;
    descProceso.textContent = proceso.descripcion;
    hojaBadge.textContent = `Hoja: ${proceso.hoja}`;

    renderEntradas(proceso);
    actualizarBotonEjecutar();
    ocultarResultado();
}

navItems.forEach((item) => {
    item.addEventListener("click", () => seleccionarProceso(item));
});

// Inicializa con el primer proceso activo
const primerItem = document.querySelector(".nav__item.is-active") || navItems[0];
if (primerItem) seleccionarProceso(primerItem);

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

// ---------- Descarga de la trama ----------
function descargarTexto(nombre, contenido) {
    const blob = new Blob([contenido], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombre || "trama.txt";
    document.body.appendChild(enlace);
    enlace.click();
    document.body.removeChild(enlace);
    URL.revokeObjectURL(url);
}

// ---------- Ejecución ----------
function setCargando(cargando) {
    const label = btnEjecutar.querySelector(".btn__label");
    const spinner = btnEjecutar.querySelector(".btn__spinner");
    btnEjecutar.disabled = cargando || !archivosCompletos();
    spinner.hidden = !cargando;
    label.textContent = cargando ? "Procesando…" : "Ejecutar proceso";
}

async function llamarProceso(url, formData) {
    setCargando(true);
    ocultarResultado();

    try {
        const resp = await fetch(url, { method: "POST", body: formData });
        const data = await resp.json();

        // Descarga la trama generada siempre que exista, haya error o no en el envío.
        if (data.trama_txt) {
            descargarTexto(data.trama_nombre, data.trama_txt);
        }

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
    if (!state.proceso || !archivosCompletos()) return;
    const formData = new FormData();
    state.proceso.entradas.forEach((entrada) => {
        formData.append(entrada.clave, state.archivos[entrada.clave]);
    });
    llamarProceso(`/api/procesar/${state.proceso.id}`, formData);
}

btnEjecutar.addEventListener("click", ejecutar);

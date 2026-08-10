// Estado de la aplicación
const state = {
    proceso: null,
    empresa: null,       // id de empresa seleccionada
    fecha: "",
    modo: "excel",       // 'excel' (todo del Excel) | 'manual' (todo escrito a mano)
    archivos: {},        // clave de entrada -> File
    params: {},          // valores de parámetros manuales
    registros: [],       // filas de datos manuales (array de objetos clave->valor)
};

// Configuración inyectada por el servidor.
const PROCESOS = window.PROCESOS || [];
const EMPRESAS = window.EMPRESAS || [];

// Referencias del DOM
const navItems = document.querySelectorAll(".nav__item");
const tituloProceso = document.getElementById("tituloProceso");
const descProceso = document.getElementById("descProceso");
const hojaBadge = document.getElementById("hojaBadge");

const entradasContainer = document.getElementById("entradas");
const entradaTemplate = document.getElementById("entradaTemplate");
const btnEjecutar = document.getElementById("btnEjecutar");

const empresaOptions = document.getElementById("empresaOptions");
const fechaField = document.getElementById("fechaField");
const fechaInput = document.getElementById("fechaInput");
const soonNote = document.getElementById("soonNote");

const stepEmpresa = document.getElementById("stepEmpresa");
const stepDatos = document.getElementById("stepDatos");
const btnCambiarEmpresa = document.getElementById("btnCambiarEmpresa");
const empresaActualNombre = document.getElementById("empresaActualNombre");
const modoParametros = document.getElementById("modoParametros");
const modoHint = document.getElementById("modoHint");
const paramForm = document.getElementById("paramForm");
const paramBlock = document.getElementById("paramBlock");
const datosBlock = document.getElementById("datosBlock");
const datosHead = document.getElementById("datosHead");
const datosBody = document.getElementById("datosBody");
const datosTable = document.getElementById("datosTable");
const datosCount = document.getElementById("datosCount");
const btnAddRegistro = document.getElementById("btnAddRegistro");
const toggleSoloUsadas = document.getElementById("toggleSoloUsadas");

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

function empresaPorId(id) {
    return EMPRESAS.find((e) => e.id === id) || null;
}

// ---------- Utilidades de archivo ----------
function extensionValida(nombre) {
    return EXTENSIONES.some((ext) => nombre.toLowerCase().endsWith(ext));
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

// ---------- Parámetros manuales ----------
function renderParamForm(proceso) {
    paramForm.innerHTML = "";
    state.params = {};
    (proceso.esquema_parametros || []).forEach((campo) => {
        const wrap = document.createElement("label");
        wrap.className = "param-field";

        const lab = document.createElement("span");
        lab.className = "param-field__label";
        lab.textContent = campo.etiqueta;

        const inp = document.createElement("input");
        inp.className = "param-field__input";
        inp.type = campo.tipo === "number" ? "number" : "text";
        inp.autocomplete = "off";
        inp.addEventListener("input", () => {
            state.params[campo.clave] = inp.value.trim();
            actualizarBotonEjecutar();
        });

        wrap.appendChild(lab);
        wrap.appendChild(inp);
        paramForm.appendChild(wrap);
    });
}

function paramsCompletos() {
    if (state.modo !== "manual") return true;
    return (state.proceso.esquema_parametros || []).every(
        (c) => (state.params[c.clave] || "").length > 0
    );
}

// ---------- Registros de datos manuales (grilla tipo Excel) ----------
function actualizarContadorRegistros() {
    const n = state.registros.length;
    datosCount.textContent = `${n} ${n === 1 ? "registro" : "registros"}`;
}

function camposDatos() {
    return state.proceso.esquema_datos || [];
}

function focoCelda(row, col) {
    const campos = camposDatos();
    if (col < 0 || col >= campos.length) return;
    if (row < 0) row = 0;
    while (row >= state.registros.length) state.registros.push({});
    renderDatosBody();
    const inp = datosBody.querySelector(`input[data-row="${row}"][data-col="${col}"]`);
    if (inp) {
        inp.focus();
        try { inp.select(); } catch (e) { /* noop */ }
    }
}

function manejarTecla(e, row, col) {
    const inp = e.target;
    const finCaret = inp.selectionStart === null || inp.selectionStart === inp.value.length;
    const inicioCaret = inp.selectionStart === null || inp.selectionStart === 0;
    if (e.key === "Enter" || e.key === "ArrowDown") {
        e.preventDefault();
        focoCelda(row + 1, col);
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        focoCelda(row - 1, col);
    } else if (e.key === "ArrowRight" && finCaret) {
        e.preventDefault();
        focoCelda(row, col + 1);
    } else if (e.key === "ArrowLeft" && inicioCaret) {
        e.preventDefault();
        focoCelda(row, col - 1);
    }
}

function manejarPegado(e, row, col) {
    const texto = (e.clipboardData || window.clipboardData).getData("text");
    // Pegado simple (una celda) se deja al comportamiento nativo.
    if (!texto || (!texto.includes("\t") && !texto.includes("\n"))) return;
    e.preventDefault();
    const campos = camposDatos();
    const filas = texto.replace(/\r/g, "").split("\n");
    if (filas.length && filas[filas.length - 1] === "") filas.pop();
    filas.forEach((linea, r) => {
        const destino = row + r;
        while (destino >= state.registros.length) state.registros.push({});
        linea.split("\t").forEach((val, c) => {
            const campo = campos[col + c];
            if (campo) state.registros[destino][campo.clave] = val.trim();
        });
    });
    renderDatosBody();
    actualizarBotonEjecutar();
    focoCelda(row, col);
}

function pintarFila(fila, indice) {
    const campos = camposDatos();
    const tr = document.createElement("tr");

    const tdNum = document.createElement("td");
    tdNum.className = "datos-table__num";
    tdNum.textContent = indice + 1;
    tr.appendChild(tdNum);

    campos.forEach((campo, col) => {
        const td = document.createElement("td");
        td.className = campo.usado ? "is-usado" : "is-opcional";
        const inp = document.createElement("input");
        inp.className = "datos-input";
        inp.type = "text";
        if (campo.tipo === "number") inp.inputMode = "decimal";
        inp.value = fila[campo.clave] ?? "";
        inp.dataset.row = indice;
        inp.dataset.col = col;
        inp.addEventListener("input", () => {
            fila[campo.clave] = inp.value;
            actualizarBotonEjecutar();
        });
        inp.addEventListener("keydown", (e) => manejarTecla(e, indice, col));
        inp.addEventListener("paste", (e) => manejarPegado(e, indice, col));
        td.appendChild(inp);
        tr.appendChild(td);
    });

    const tdAcc = document.createElement("td");
    tdAcc.className = "datos-table__acc";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "datos-remove";
    btn.title = "Quitar registro";
    btn.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 7h12M9 7V5h6v2M10 11v6M14 11v6M7 7l1 12a1 1 0 001 1h6a1 1 0 001-1l1-12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    btn.addEventListener("click", () => quitarRegistro(indice));
    tdAcc.appendChild(btn);
    tr.appendChild(tdAcc);

    return tr;
}

function renderDatosBody() {
    datosBody.innerHTML = "";
    state.registros.forEach((fila, i) => datosBody.appendChild(pintarFila(fila, i)));
    actualizarContadorRegistros();
}

function renderDatosTabla(proceso) {
    state.registros = [];
    const campos = proceso.esquema_datos || [];

    datosHead.innerHTML = "";
    const trh = document.createElement("tr");
    const thNum = document.createElement("th");
    thNum.className = "datos-table__num";
    thNum.textContent = "#";
    trh.appendChild(thNum);
    campos.forEach((campo) => {
        const th = document.createElement("th");
        th.className = campo.usado ? "is-usado" : "is-opcional";
        th.textContent = campo.etiqueta;
        if (!campo.usado) th.title = "Columna del Excel no usada por este proceso";
        trh.appendChild(th);
    });
    const thAcc = document.createElement("th");
    thAcc.setAttribute("aria-label", "Acciones");
    trh.appendChild(thAcc);
    datosHead.appendChild(trh);

    aplicarFiltroColumnas();
    // Empieza con una fila lista para escribir.
    state.registros.push({});
    renderDatosBody();
}

function aplicarFiltroColumnas() {
    if (!datosTable) return;
    const solo = Boolean(toggleSoloUsadas && toggleSoloUsadas.checked);
    datosTable.classList.toggle("datos-table--solo-usadas", solo);
}

function agregarRegistro() {
    state.registros.push({});
    renderDatosBody();
    actualizarBotonEjecutar();
    focoCelda(state.registros.length - 1, 0);
}

function quitarRegistro(indice) {
    state.registros.splice(indice, 1);
    if (state.registros.length === 0) state.registros.push({});
    renderDatosBody();
    actualizarBotonEjecutar();
}

function datosCompletos() {
    // Solo son obligatorias las columnas que el proceso realmente usa.
    const campos = (state.proceso.esquema_datos || []).filter((c) => c.usado);
    if (state.registros.length === 0) return false;
    return state.registros.every((fila) =>
        campos.every((c) => String(fila[c.clave] ?? "").trim().length > 0)
    );
}

if (btnAddRegistro) btnAddRegistro.addEventListener("click", agregarRegistro);
if (toggleSoloUsadas) toggleSoloUsadas.addEventListener("change", aplicarFiltroColumnas);

// ---------- Requisitos ----------
function archivosCompletos() {
    if (!state.proceso) return false;
    return state.proceso.entradas.every((e) => Boolean(state.archivos[e.clave]));
}

function fechaValida() {
    return /^\d{8}$/.test(state.fecha);
}

function requisitosCompletos() {
    const p = state.proceso;
    if (!p || !p.disponible || !state.empresa) return false;
    if (p.requiere_fecha && !fechaValida()) return false;
    if (state.modo === "manual") {
        return paramsCompletos() && datosCompletos();
    }
    return archivosCompletos();
}

function actualizarBotonEjecutar() {
    btnEjecutar.disabled = !requisitosCompletos();
}

// ---------- Modo (Excel / manual) ----------
function setModo(modo) {
    state.modo = modo;
    document.querySelectorAll(".modo__tab").forEach((t) =>
        t.classList.toggle("is-active", t.dataset.modo === modo)
    );

    const manual = modo === "manual";
    const tieneParams = (state.proceso.esquema_parametros || []).length > 0;

    // En manual: parámetros + registros, sin Excel. En excel: solo carga de archivo.
    paramBlock.hidden = !(manual && tieneParams);
    datosBlock.hidden = !manual;
    entradasContainer.hidden = manual;

    modoHint.textContent = manual
        ? "Escribe los parámetros y uno o más registros. La compañía se toma de la empresa elegida."
        : "Sube el Excel; los datos y parámetros se leen de sus hojas.";

    actualizarBotonEjecutar();
}

document.querySelectorAll(".modo__tab").forEach((tab) => {
    tab.addEventListener("click", () => setModo(tab.dataset.modo));
});

// ---------- Navegación entre procesos ----------
function seleccionarProceso(item) {
    navItems.forEach((n) => n.classList.remove("is-active"));
    item.classList.add("is-active");

    const proceso = procesoPorId(item.dataset.proceso);
    state.proceso = proceso;
    state.empresa = null;
    state.fecha = "";
    if (fechaInput) fechaInput.value = "";

    tituloProceso.textContent = proceso.nombre;
    descProceso.textContent = proceso.descripcion;
    hojaBadge.textContent = `Hoja: ${proceso.hoja}`;

    ocultarResultado();

    if (!proceso.disponible) {
        soonNote.hidden = false;
        stepEmpresa.hidden = true;
        stepDatos.hidden = true;
        return;
    }

    soonNote.hidden = true;
    stepEmpresa.hidden = false;
    stepDatos.hidden = true;

    empresaOptions.querySelectorAll(".empresa-card").forEach((c) => c.classList.remove("is-active"));

    fechaField.hidden = !proceso.requiere_fecha;
    modoParametros.hidden = !proceso.admite_manual;
    renderEntradas(proceso);
    renderParamForm(proceso);
    renderDatosTabla(proceso);
    setModo("excel");
}

navItems.forEach((item) => {
    item.addEventListener("click", () => seleccionarProceso(item));
});

// ---------- Selección de empresa (paso 1 -> paso 2) ----------
function seleccionarEmpresa(id) {
    state.empresa = id;
    empresaOptions.querySelectorAll(".empresa-card").forEach((c) =>
        c.classList.toggle("is-active", c.dataset.empresa === id)
    );
    const emp = empresaPorId(id);
    empresaActualNombre.textContent = emp ? emp.corto : id;
    stepDatos.hidden = false;
    actualizarBotonEjecutar();
    stepDatos.scrollIntoView({ behavior: "smooth", block: "start" });
}

if (empresaOptions) {
    empresaOptions.querySelectorAll(".empresa-card").forEach((card) => {
        card.addEventListener("click", () => seleccionarEmpresa(card.dataset.empresa));
    });
}

if (btnCambiarEmpresa) {
    btnCambiarEmpresa.addEventListener("click", () => {
        stepDatos.hidden = true;
        stepEmpresa.scrollIntoView({ behavior: "smooth", block: "start" });
    });
}

if (fechaInput) {
    fechaInput.addEventListener("input", (e) => {
        state.fecha = e.target.value.replace(/\D/g, "").slice(0, 8);
        e.target.value = state.fecha;
        actualizarBotonEjecutar();
    });
}

// Inicializa con el primer proceso activo.
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
    btnEjecutar.disabled = cargando || !requisitosCompletos();
    spinner.hidden = !cargando;
    label.textContent = cargando ? "Procesando…" : "Ejecutar proceso";
}

async function llamarProceso(url, formData) {
    setCargando(true);
    ocultarResultado();

    try {
        const resp = await fetch(url, { method: "POST", body: formData });
        const data = await resp.json();

        if (data.trama_txt) {
            descargarTexto(data.trama_nombre, data.trama_txt);
        }

        const meta = data.registros != null ? `${data.registros} registro(s)` : "";
        if (data.ok) {
            mostrarResultado(true, "Proceso exitoso", data.mensaje || "Ejecutado correctamente.", meta, data.respuesta || "", {
                etiquetaDetalle: "Ver respuesta del servicio",
            });
        } else {
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
    if (!requisitosCompletos()) return;
    const formData = new FormData();
    formData.append("empresa", state.empresa);
    if (state.proceso.requiere_fecha) {
        formData.append("fecha", state.fecha);
    }
    formData.append("modo_parametros", state.modo);

    if (state.modo === "manual") {
        Object.entries(state.params).forEach(([clave, valor]) => {
            formData.append(`param_${clave}`, valor);
        });
        formData.append("datos", JSON.stringify(state.registros));
    } else {
        state.proceso.entradas.forEach((entrada) => {
            formData.append(entrada.clave, state.archivos[entrada.clave]);
        });
    }

    llamarProceso(`/api/procesar/${state.proceso.id}`, formData);
}

btnEjecutar.addEventListener("click", ejecutar);

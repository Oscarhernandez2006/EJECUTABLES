(() => {
    const panel = document.getElementById("tallerPanel");
    const el = (nombre) => document.getElementById(`taller${nombre}`);
    const moneda = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 2 });
    const decimal = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 4 });
    const porcentaje = (valor) => `${decimal.format(valor * 100)} %`;
    const controles = {};
    const filas = { insumos: [], productos: [] };
    let pendientes = [];
    let empresa = "";
    let generacion = 0;
    let ocupado = false;
    let confirmado = false;
    let consultaActual = 0;
    let configurado = false;
    let revision = "";
    let soloHoy = false;

    function iconos() { window.lucide?.createIcons({ root: panel }); }
    function error(mensaje = "") {
        el("Error").textContent = mensaje;
        el("Error").hidden = !mensaje;
    }
    function filtros(extra = {}) {
        return { empresa, fecha: el("Fecha").value.replaceAll("-", ""),
            co: controles.Centro?.getValue() || "", lista: controles.Lista?.getValue() || "", ...extra };
    }
    async function peticion(url, opciones = {}) {
        const respuesta = await fetch(url, { cache: "no-store", ...opciones });
        const tipo = respuesta.headers.get("content-type") || "";
        if (!tipo.includes("application/json")) throw new Error("El servidor no pudo completar la solicitud.");
        const datos = await respuesta.json();
        if (!respuesta.ok || !datos.ok) throw new Error(datos.mensaje || "No se pudo completar la consulta.");
        return datos;
    }
    async function catalogo(recurso, extra = {}, signal) {
        return (await peticion(`/api/taller/catalogo/${recurso}?${new URLSearchParams(filtros(extra))}`, { signal })).datos;
    }
    function selector(nodo, placeholder, recurso, extra, cambio) {
        let solicitud;
        const control = new TomSelect(nodo, {
            valueField: "codigo", labelField: "etiqueta", searchField: ["codigo", "descripcion", "referencia"],
            placeholder, maxItems: 1, create: false, loadThrottle: 300, preload: false,
            dropdownParent: "body", plugins: ["clear_button"],
            render: {
                no_results: () => '<div class="no-results">Sin coincidencias</div>',
                loading: () => '<div class="loading">Consultando Siesa...</div>',
            },
            onType: function (consulta) {
                this.loadedSearches = {};
                if (this.settings.shouldLoad(consulta)) this.load(consulta);
            },
            onDropdownOpen: function () {
                this.loadedSearches = {};
                const consulta = this.control_input.value;
                if (this.settings.shouldLoad(consulta)) this.load(consulta);
            },
            shouldLoad: (consulta) => configurado && (recurso !== "productos" || consulta.trim().length >= 1)
                && (recurso !== "bodegas" || !!controles.Centro?.getValue())
                && (recurso !== "lotes" || !!extra().item && !!extra().bodega),
            load: async (consulta, callback) => {
                solicitud?.abort();
                solicitud = new AbortController();
                const actual = generacion;
                try {
                    const respuesta = await catalogo(recurso, { ...extra(), q: consulta }, solicitud.signal);
                    const datos = Array.isArray(respuesta) ? respuesta : respuesta.data;
                    if (actual !== generacion) return callback();
                    control.clearOptions();
                    callback(datos.map((dato) => ({ ...dato, etiqueta: `${dato.codigo} · ${dato.descripcion}` })));
                } catch (fallo) {
                    callback();
                    if (fallo.name !== "AbortError" && actual === generacion) error(fallo.message);
                }
            },
            onChange: () => { if (!ocupado) cambio?.(); },
        });
        control.on("destroy", () => solicitud?.abort());
        return control;
    }
    async function cargarControl(nombre, recurso, extra = {}) {
        const control = controles[nombre];
        const actual = generacion;
        control.clear(true);
        control.clearOptions();
        if (!configurado) return;
        const datos = await catalogo(recurso, extra);
        if (actual !== generacion) return;
        control.addOptions(datos.map((dato) => ({ ...dato, etiqueta: `${dato.codigo} · ${dato.descripcion}` })));
    }
    function bodega(grupo) { return controles[grupo === "insumos" ? "Origen" : "Destino"]?.getValue() || ""; }
    function agregar(grupo, inicial = null) {
        const fila = { grupo, detalle: null, version: 0, cantidad: inicial?.cantidad || "", precio: "", modificado: false, manejaLote: false };
        const tr = document.createElement("tr");
        const columnas = grupo === "insumos" ? 8 : 10;
        for (let indice = 0; indice < columnas; indice++) tr.appendChild(document.createElement("td"));
        const producto = document.createElement("select");
        producto.setAttribute("aria-label", grupo === "insumos" ? "Buscar insumo por ítem o nombre" : "Buscar producto por ítem o nombre");
        const estado = document.createElement("small");
        estado.setAttribute("role", "status");
        tr.children[0].append(producto, estado);
        const lote = document.createElement("select");
        lote.setAttribute("aria-label", "Lote");
        tr.children[1].appendChild(lote);
        const cantidad = document.createElement("input");
        cantidad.type = "number"; cantidad.min = "0.0001"; cantidad.step = "0.0001";
        cantidad.value = fila.cantidad; cantidad.setAttribute("aria-label", "Cantidad");
        tr.children[3].appendChild(cantidad);
        fila.cantidadInput = cantidad;
        cantidad.addEventListener("input", () => { fila.cantidad = cantidad.value; error(); recalcular(); });
        for (const indice of grupo === "insumos" ? [2, 4, 5, 6] : [2, 4, 6, 7, 8]) {
            tr.children[indice].appendChild(document.createElement("output"));
        }
        if (grupo === "productos") {
            const precio = document.createElement("input");
            precio.type = "number"; precio.min = "0"; precio.step = "0.01";
            precio.setAttribute("aria-label", "Precio de venta editable");
            precio.addEventListener("input", () => {
                fila.precio = precio.value; fila.modificado = true; error(); recalcular();
            });
            fila.precioInput = precio;
            tr.children[5].appendChild(precio);
        }
        const quitar = document.createElement("button");
        quitar.type = "button"; quitar.className = "taller__icon";
        quitar.title = "Quitar fila"; quitar.setAttribute("aria-label", "Quitar fila");
        quitar.innerHTML = '<i data-lucide="trash-2"></i>';
        quitar.onclick = () => {
            fila.version++; fila.producto.destroy(); fila.lote.destroy(); tr.remove();
            filas[grupo].splice(filas[grupo].indexOf(fila), 1); recalcular();
        };
        tr.lastElementChild.appendChild(quitar);
        el(grupo === "insumos" ? "Insumos" : "Productos").appendChild(tr);
        fila.tr = tr; fila.estado = estado;
        fila.producto = selector(producto, "Ítem o nombre...", "productos", () => ({ bodega: bodega(grupo) }), () => {
            fila.modificado = false; fila.precio = "";
            if (fila.precioInput) fila.precioInput.value = "";
            actualizarFila(fila, true);
        });
        fila.lote = selector(lote, "Sin lote", "lotes", () => ({ item: fila.producto.getValue(), bodega: bodega(grupo),
            solo_con_existencia: grupo === "insumos" ? "true" : "false" }),
            () => actualizarFila(fila));
        filas[grupo].push(fila);
        if (inicial) {
            fila.producto.addOption({ codigo: inicial.item, descripcion: inicial.descripcion, etiqueta: `${inicial.item} · ${inicial.descripcion}` });
            fila.producto.setValue(inicial.item, true);
            fila.precio = inicial.precio_venta ?? ""; fila.modificado = grupo === "productos" && (inicial.precio_editado ?? true);
            fila.loteInicial = inicial.lote;
            actualizarFila(fila, true);
        }
        iconos(); recalcular();
    }
    async function actualizarFila(fila, recargarLotes = false) {
        const version = ++fila.version;
        const actual = generacion;
        const item = fila.producto.getValue();
        fila.detalle = null;
        fila.estado.textContent = "";
        recalcular();
        if (!item || !bodega(fila.grupo) || !controles.Lista.getValue()) return;
        fila.estado.textContent = "Consultando...";
        try {
            if (recargarLotes) {
                fila.lote.clear(true); fila.lote.clearOptions();
                const respuestaLotes = await catalogo("lotes", { item, bodega: bodega(fila.grupo),
                    solo_con_existencia: fila.grupo === "insumos" ? "true" : "false" });
                if (version !== fila.version || actual !== generacion) return;
                const lotes = Array.isArray(respuestaLotes) ? respuestaLotes : respuestaLotes.data;
                fila.manejaLote = Array.isArray(respuestaLotes) ? lotes.length > 0 : respuestaLotes.maneja_lote;
                fila.lote.addOptions(lotes.map((dato) => ({ ...dato, etiqueta: `${dato.codigo} · ${dato.descripcion}` })));
                if (fila.loteInicial) { fila.lote.setValue(fila.loteInicial, true); fila.loteInicial = null; }
            }
            if (fila.manejaLote && !fila.lote.getValue()) {
                fila.estado.textContent = fila.lote.options && Object.keys(fila.lote.options).length
                    ? "Selecciona un lote" : "Sin lotes disponibles. Crea el lote en Siesa antes del movimiento.";
                return;
            }
            const detalle = await catalogo("detalle", { item, bodega: bodega(fila.grupo), lote: fila.lote.getValue() });
            if (version !== fila.version || actual !== generacion) return;
            fila.detalle = detalle;
            if (!fila.modificado) fila.precio = detalle.tiene_precio === false ? "" : detalle.precio_venta;
            if (fila.precioInput) fila.precioInput.value = fila.precio;
            const avisos = Array.isArray(detalle.avisos) ? detalle.avisos.filter((aviso) => typeof aviso === "string") : [];
            if (fila.grupo === "insumos" && detalle.tiene_costo === false) avisos.push("Sin costo en Siesa: insumo bloqueado.");
            if (fila.grupo === "productos" && detalle.tiene_precio === false) avisos.push("Sin precio vigente: ingresa el precio de venta.");
            if (fila.grupo === "productos" && typeof detalle.incluye_impuestos === "boolean") avisos.push(
                detalle.incluye_impuestos ? "Precio con impuestos incluidos." : "Precio sin impuestos.");
            fila.estado.textContent = avisos.join(" ");
            if (fila.precioInput) fila.precioInput.title = detalle.incluye_impuestos ? "Precio con impuestos incluidos" : "Precio sin impuestos";
            el("Sync").textContent = `Siesa · ${new Date().toLocaleTimeString("es-CO")}`;
        } catch (fallo) {
            if (version === fila.version && actual === generacion) fila.estado.textContent = fallo.message;
        } finally { recalcular(); }
    }
    function limpiarFilas() {
        for (const grupo of Object.keys(filas)) {
            for (const fila of filas[grupo]) { fila.version++; fila.producto.destroy(); fila.lote.destroy(); fila.tr.remove(); }
            filas[grupo] = [];
        }
    }
    function datosFila(fila) {
        return { item: fila.producto.getValue(), descripcion: fila.detalle?.descripcion || "", lote: fila.lote.getValue(),
            bodega: bodega(fila.grupo), cantidad: Number(fila.cantidad), precio_venta: Number(fila.precio),
            precio_editado: fila.modificado, costo_promedio: fila.detalle?.costo_promedio, um: fila.detalle?.um };
    }
    function calcularLocal(insumos, productos) {
        const costo = insumos.reduce((suma, fila) => suma + fila.cantidad * (fila.costo_promedio || 0), 0);
        const venta = productos.reduce((suma, fila) => suma + fila.cantidad * fila.precio_venta, 0);
        const pesoInsumos = insumos.reduce((suma, fila) => suma + fila.cantidad, 0);
        const pesoProductos = productos.reduce((suma, fila) => suma + fila.cantidad, 0);
        return { costo, venta, utilidad: venta - costo, margen: venta ? (venta - costo) / venta : 0,
            pesoInsumos, pesoProductos, merma: pesoInsumos - pesoProductos };
    }
    function recalcular() {
        const insumos = filas.insumos.map(datosFila);
        const productos = filas.productos.map(datosFila);
        const total = calcularLocal(insumos, productos);
        const consumos = new Map();
        for (const taller of pendientes) for (const fila of taller.insumos) {
            const clave = [fila.bodega, fila.item, fila.lote].join("|");
            consumos.set(clave, (consumos.get(clave) || 0) + fila.cantidad);
        }
        let completo = configurado && !!controles.Centro?.getValue() && !!controles.Lista?.getValue();
        for (const grupo of Object.keys(filas)) {
            if (!filas[grupo].length) completo = false;
            filas[grupo].forEach((fila) => {
                const datos = datosFila(fila);
                const pintar = (indice, valor) => { fila.tr.children[indice].querySelector("output").textContent = valor; };
                pintar(2, fila.detalle ? decimal.format(fila.detalle.existencia) : "—");
                pintar(4, fila.detalle?.um || "—");
                let insuficiente = false;
                if (grupo === "insumos") {
                    const clave = [datos.bodega, datos.item, datos.lote].join("|");
                    consumos.set(clave, (consumos.get(clave) || 0) + datos.cantidad);
                    insuficiente = !!fila.detalle && consumos.get(clave) > fila.detalle.existencia;
                    pintar(5, fila.detalle?.tiene_costo === false ? "Sin costo" : fila.detalle ? moneda.format(datos.costo_promedio) : "—");
                    pintar(6, fila.detalle && fila.detalle.tiene_costo !== false ? moneda.format(datos.cantidad * datos.costo_promedio) : "—");
                    if (fila.detalle?.tiene_costo === false) completo = false;
                } else {
                    pintar(6, porcentaje(total.pesoInsumos ? datos.cantidad / total.pesoInsumos : 0));
                    pintar(7, total.venta ? moneda.format(Math.round(datos.precio_venta * total.costo / total.venta * 100) / 100) : "—");
                    pintar(8, moneda.format(datos.cantidad * datos.precio_venta));
                }
                fila.cantidadInput.setAttribute("aria-invalid", String(insuficiente || Number(fila.cantidad) <= 0));
                fila.cantidadInput.title = insuficiente ? "Supera la existencia disponible, incluido el consolidado" : "Cantidad";
                if (!fila.detalle || !Number.isFinite(datos.cantidad) || datos.cantidad <= 0 || insuficiente ||
                    !Number.isFinite(datos.precio_venta) || datos.precio_venta < 0 || (grupo === "productos" && fila.precio === "")) completo = false;
                if (grupo === "productos" && fila.detalle?.tiene_precio === false && !fila.modificado) completo = false;
            });
        }
        for (const [nombre, valor] of Object.entries({ Costo: total.costo, Venta: total.venta, Utilidad: total.utilidad })) el(nombre).textContent = moneda.format(valor);
        el("Utilidad").classList.toggle("taller__negative", total.utilidad < 0);
        el("Margen").textContent = porcentaje(total.margen);
        el("CostoVenta").textContent = porcentaje(total.venta ? total.costo / total.venta : 0);
        el("PesoInsumos").textContent = decimal.format(total.pesoInsumos);
        el("PesoProductos").textContent = decimal.format(total.pesoProductos);
        el("Merma").textContent = decimal.format(total.merma);
        el("Merma").classList.toggle("taller__negative", total.merma < 0);
        el("Rendimiento").textContent = porcentaje(total.pesoInsumos ? total.pesoProductos / total.pesoInsumos : 0);
        const unidades = new Set([...insumos, ...productos].map((fila) => fila.um?.trim().toLowerCase()).filter(Boolean));
        if (unidades.size > 1) {
            el("Merma").textContent = "UM diferentes"; el("Rendimiento").textContent = "—";
            completo = false;
        }
        el("Consolidar").disabled = ocupado || !completo || total.venta <= 0;
        el("Enviar").disabled = ocupado || !pendientes.length;
        el("Exportar").disabled = ocupado || !pendientes.length;
    }
    function renderConsolidado() {
        el("Consolidado").hidden = !pendientes.length;
        el("Cuenta").textContent = `${pendientes.length} talleres`;
        el("ConsolidadoBody").replaceChildren();
        let costo = 0; let venta = 0;
        pendientes.forEach((taller, indice) => {
            const total = calcularLocal(taller.insumos, taller.productos);
            costo += total.costo; venta += total.venta;
            const tr = document.createElement("tr");
            for (const valor of [taller.numero, taller.insumos.length, taller.productos.length, moneda.format(total.costo),
                moneda.format(total.venta), moneda.format(total.utilidad), porcentaje(total.margen)]) {
                const td = document.createElement("td"); td.textContent = valor; tr.appendChild(td);
            }
            const acciones = document.createElement("td");
            for (const [icono, titulo, accion] of [
                ["pencil", "Editar taller", () => editar(indice)],
                ["trash-2", "Quitar taller", () => { pendientes.splice(indice, 1); renderConsolidado(); }],
            ]) {
                const boton = document.createElement("button"); boton.type = "button"; boton.className = "taller__icon";
                boton.title = titulo; boton.setAttribute("aria-label", titulo); boton.disabled = ocupado;
                boton.innerHTML = `<i data-lucide="${icono}"></i>`; boton.onclick = accion; acciones.appendChild(boton);
            }
            tr.appendChild(acciones); el("ConsolidadoBody").appendChild(tr);
        });
        el("Acumulado").textContent = `Costo ${moneda.format(costo)} · Venta ${moneda.format(venta)} · Utilidad ${moneda.format(venta - costo)} · Margen ${porcentaje(venta ? (venta - costo) / venta : 0)}`;
        for (const nombre of ["Centro", "Lista", "Origen", "Destino"]) {
            if (pendientes.length || ocupado) controles[nombre]?.disable(); else controles[nombre]?.enable();
        }
        el("Fecha").disabled = soloHoy || !!pendientes.length || ocupado;
        iconos(); recalcular();
    }
    function editar(indice) {
        if ([...filas.insumos, ...filas.productos].some((fila) => fila.producto.getValue()) &&
            !confirm("¿Reemplazar la captura actual por este taller?")) return;
        const taller = pendientes.splice(indice, 1)[0];
        limpiarFilas(); el("Numero").value = taller.numero;
        for (const grupo of Object.keys(filas)) taller[grupo].forEach((fila) => agregar(grupo, fila));
        renderConsolidado();
    }
    function consolidar() {
        error();
        const numero = Number(el("Numero").value);
        if (!Number.isInteger(numero) || numero < 1 || numero > 99999999) return error("El número de taller debe ser un entero entre 1 y 99999999.");
        if (pendientes.some((taller) => taller.numero === numero)) return error("Este número de taller ya está en el consolidado.");
        if (pendientes.length >= 30) return error("El máximo es de 30 talleres por envío.");
        if (filas.insumos.length > 100 || filas.productos.length > 100) return error("El máximo es de 100 filas por grupo.");
        pendientes.push({ numero, insumos: filas.insumos.map(datosFila), productos: filas.productos.map(datosFila) });
        limpiarFilas(); agregar("insumos"); agregar("productos");
        el("Numero").value = Math.max(...pendientes.map((taller) => taller.numero)) + 1;
        renderConsolidado();
    }
    function payload() { return { ...filtros(), talleres: pendientes, revision }; }
    function bloquear(valor) {
        ocupado = valor;
        panel.setAttribute("aria-busy", String(valor));
        for (const nombre of ["Actualizar", "AgregarInsumo", "AgregarProducto", "Excel", "Numero", "Confirmar", "CambiarEmpresa"]) el(nombre).disabled = valor;
        for (const fila of [...filas.insumos, ...filas.productos]) {
            fila.cantidadInput.disabled = valor;
            if (fila.precioInput) fila.precioInput.disabled = valor;
            if (valor) { fila.producto.disable(); fila.lote.disable(); } else { fila.producto.enable(); fila.lote.enable(); }
            fila.tr.querySelector("button.taller__icon").disabled = valor;
        }
        renderConsolidado();
    }
    async function validar() {
        if ([...filas.insumos, ...filas.productos].some((fila) => fila.producto.getValue())) {
            error("Consolida o elimina la captura actual antes de importar el acumulado."); return;
        }
        error(); bloquear(true);
        try {
            const resultado = await peticion("/api/taller/validar", {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()),
            });
            const resumen = resultado.resumen;
            revision = resultado.revision;
            el("ConfirmacionTexto").textContent = `${pendientes.length} talleres · ${el("Empresa").textContent}\nFecha: ${el("Fecha").value}\nCosto actualizado: ${moneda.format(resumen.costo_total)}\nVenta: ${moneda.format(resumen.venta_total)}\nUtilidad: ${moneda.format(resumen.utilidad)}\nMargen: ${porcentaje(resumen.margen)}`;
            confirmado = true;
            el("Confirmar").disabled = false;
            el("Confirmacion").showModal();
        } catch (fallo) { error(fallo.message); bloquear(false); }
    }
    async function enviar() {
        if (!confirmado) return;
        confirmado = false; el("Confirmar").disabled = true;
        el("ConfirmacionTexto").textContent = "Importando documentos a Siesa...";
        el("Cancelar").disabled = true;
        try {
            const resultado = await peticion("/api/taller/ejecutar", {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()),
            });
            pendientes = [];
            el("Aviso").textContent = resultado.mensaje;
            el("Aviso").hidden = false;
        } catch (fallo) { error(`${fallo.message} Antes de reenviar, verifica en Siesa si algún documento ya fue importado.`); }
        finally {
            el("Confirmacion").close(); el("Cancelar").disabled = false; bloquear(false); actualizarTodo();
        }
    }
    async function exportar() {
        bloquear(true); error();
        try {
            const respuesta = await fetch("/api/taller/exportar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()) });
            if (!respuesta.ok) throw new Error((await respuesta.json()).mensaje || "No se pudo exportar.");
            const url = URL.createObjectURL(await respuesta.blob());
            const enlace = document.createElement("a"); enlace.href = url; enlace.download = `Taller-${filtros().fecha}.xlsx`; enlace.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (fallo) { error(fallo.message); } finally { bloquear(false); }
    }
    async function actualizarTodo() {
        if (ocupado || !configurado || panel.hidden) return;
        error(); el("Sync").textContent = "Actualizando Siesa...";
        const actual = ++consultaActual;
        await Promise.all([...filas.insumos, ...filas.productos].map((fila) => actualizarFila(fila)));
        if (actual === consultaActual && !panel.hidden) el("Sync").textContent = `Consulta finalizada · ${new Date().toLocaleTimeString("es-CO")}`;
    }
    async function cambiarCentro() {
        if (ocupado) return;
        generacion++;
        controles.Origen.clear(true); controles.Destino.clear(true);
        for (const fila of [...filas.insumos, ...filas.productos]) { fila.version++; fila.detalle = null; }
        recalcular();
        try {
            await Promise.all([cargarControl("Origen", "bodegas"), cargarControl("Destino", "bodegas")]);
        } catch (fallo) { error(fallo.message); }
    }
    async function abrir(id, nombre) {
        panel.hidden = false;
        if (empresa === id && controles.Centro) return;
        empresa = id; generacion++; pendientes = []; configurado = false; error();
        soloHoy = id === "8";
        limpiarFilas();
        for (const control of Object.values(controles)) control.destroy();
        el("Empresa").textContent = nombre;
        const hoy = new Date();
        el("Fecha").value = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, "0")}-${String(hoy.getDate()).padStart(2, "0")}`;
        el("Fecha").removeAttribute("min"); el("Fecha").removeAttribute("max");
        el("Numero").value = 1;
        if (!window.TomSelect) { error("No se pudieron cargar los selectores. Revisa la conexión y recarga la página."); return; }
        controles.Centro = selector(el("Centro"), "Centro de operación", "centros", () => ({}), cambiarCentro);
        controles.Lista = selector(el("Lista"), "Lista de precios", "listas", () => ({}), actualizarTodo);
        controles.Origen = selector(el("Origen"), "Bodega de insumos", "bodegas", () => ({}), () => {
            filas.insumos.forEach((fila) => actualizarFila(fila, true));
        });
        controles.Destino = selector(el("Destino"), "Bodega de terminados", "bodegas", () => ({}), () => {
            filas.productos.forEach((fila) => actualizarFila(fila, true));
        });
        agregar("insumos"); agregar("productos"); renderConsolidado();
        const actual = generacion;
        try {
            const datos = await peticion(`/api/taller/configuracion?empresa=${encodeURIComponent(empresa)}`);
            if (actual !== generacion) return;
            configurado = datos.disponible;
            soloHoy = datos.solo_hoy;
            if (soloHoy) {
                const fecha = datos.fecha_hoy;
                el("Fecha").value = `${fecha.slice(0, 4)}-${fecha.slice(4, 6)}-${fecha.slice(6, 8)}`;
            }
            el("Aviso").hidden = configurado && !soloHoy;
            el("Aviso").textContent = configurado
                ? (soloHoy ? "Existencias y costos al corte de hoy (Colombia). Los lotes nuevos deben estar creados en Siesa." : "")
                : `Conexión de lectura pendiente. Falta configurar en este servidor: ${datos.faltantes.join(", ")}.`;
            if (configurado) await Promise.all([cargarControl("Centro", "centros"), cargarControl("Lista", "listas")]);
        } catch (fallo) { error(fallo.message); }
        renderConsolidado(); iconos();
    }
    el("Fecha").addEventListener("change", () => { generacion++; actualizarTodo(); });
    el("AgregarInsumo").onclick = () => agregar("insumos");
    el("AgregarProducto").onclick = () => agregar("productos");
    el("Consolidar").onclick = consolidar;
    el("Actualizar").onclick = actualizarTodo;
    el("Enviar").onclick = validar;
    el("Exportar").onclick = exportar;
    el("Confirmar").onclick = enviar;
    el("Cancelar").onclick = () => { confirmado = false; el("Confirmacion").close(); bloquear(false); };
    el("Confirmacion").addEventListener("cancel", (evento) => {
        if (!confirmado) evento.preventDefault(); else { confirmado = false; bloquear(false); }
    });
    el("Excel").onclick = () => { panel.hidden = true; document.getElementById("stepDatos").hidden = false; };
    el("CambiarEmpresa").onclick = () => {
        if (ocupado) return;
        if ((pendientes.length || [...filas.insumos, ...filas.productos].some((fila) => fila.producto.getValue())) &&
            !confirm("¿Cambiar de empresa? Al elegir otra empresa se descartará la captura y el consolidado actuales.")) return;
        panel.hidden = true; document.getElementById("stepEmpresa").hidden = false;
    };
    document.addEventListener("visibilitychange", () => { if (!document.hidden) actualizarTodo(); });
    window.addEventListener("beforeunload", (evento) => {
        if (pendientes.length || [...filas.insumos, ...filas.productos].some((fila) => fila.producto.getValue())) evento.preventDefault();
    });
    window.Taller = { abrir, estaOcupado: () => ocupado, ocultar: () => { panel.hidden = true; } };
})();
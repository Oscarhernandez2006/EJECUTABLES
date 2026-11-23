# Ejecutables · Procesador de Integraciones Siesa

Interfaz web para cargar archivos Excel y ejecutar los procesos de importación
hacia el servicio web (SOAP) de Siesa.

**Integración Suite SCTOOLS**: Esta aplicación está registrada en el hub de
aplicaciones de SCTOOLS (`ejecutables`) y es accesible desde el portal principal
para usuarios con permiso.

## Procesos disponibles

| Proceso        | Hoja Excel      | Tipos de registro |
| -------------- | --------------- | ----------------- |
| Pedidos        | `PEDIDO`        | 430 / 431         |
| Requisiciones  | `TRASNFERENCIA` | 440 / 441         |
| Sobrecostos    | `SOBRECOSTOS`   | 451 / 452         |

Estos tres procesos usan además las hojas `EQUIVALENTES` y `PARAMETROS`.

### Inventario: Taller y Saldos Iniciales (SIINV)

Disponibles en el grupo **Inventario**, mediante Excel o tablas manuales pegadas
desde Excel. Ambos requieren empresa y fecha; **la fecha seleccionada en la web
se aplica a todos los documentos**, reemplazando la columna `FECHA` de la carga.
La `CIA` del Excel se valida contra la empresa seleccionada.

| Proceso | Plantilla | Hoja / encabezados | Documentos |
| --- | --- | --- | --- |
| Taller | `Taller.xlsx` | `Hoja1`, fila 1 | Salida SAI (62/602/04), entrada EIN (61/601/04) |
| SIINV | `PLANT3.xlsx` | `Hoja1`, fila 1 | SIN (61/601/99) |

Ambos generan encabezados 450 versión 2 y movimientos 470 versión 12. Se
conservan `CO`, `NUMERO`, `BODEGA`, `REFERENCIA`, `LOTE`, `UM` y `CANT` de cada
fila; `LOTE` puede quedar vacío cuando no aplica, pero no se recorta si excede
15 caracteres. Las unidades se envían en minúsculas, como en los demás procesos.

**Taller** exige salidas y entradas con el mismo `CO` y `NUMERO`. Suma el
`COSTO UNITARIO × CANT` de **todas** las salidas de esa transformación y lo
distribuye entre las entradas proporcionalmente a `PRECIO DE  VENTA × CANT`.
El costo unitario de entrada se redondea a dos decimales, como en el original;
el total reconstruido puede tener diferencias de redondeo. No se toma solo la
última salida ni se cruzan costos entre centros de operación.
Las entradas no requieren costo diligenciado y las salidas no requieren precio
de venta. Las parejas incompletas se rechazan antes del envío.

**SIINV** toma `COSTO_UNITARIO` directamente de cada fila y no realiza reparto
de costos. Solo admite documentos `SIN`.

En modo Excel se conservan los valores originales de unidad de negocio (`001`)
y tercero (`900326452` para Taller, `generico` para SIINV). El modo manual permite
especificarlos. Los documentos se envían por lotes sin partir un documento ni
separar la salida y entrada de una transformación. El resultado permite descargar
la trama generada.

Usan la conexión compartida de la web y sus credenciales de entorno
`SIESA_USER` / `SIESA_PASSWORD`; se pueden sobrescribir por proceso mediante
`SIESA_TALLER_USER` / `SIESA_TALLER_PASSWORD` y
`SIESA_SIINV_USER` / `SIESA_SIINV_PASSWORD`. No se reutilizan las credenciales
personales ni la conexión de pruebas incrustadas en los scripts de escritorio.

### Taller interactivo con consultas a Siesa

Al seleccionar **Inventario > Taller** y una empresa se abre la captura
interactiva. **Cargar Excel** conserva el flujo de importación anterior.
Centro, lista de precios, bodegas, productos y lotes usan selectores buscables.
La búsqueda de productos admite código, referencia o descripción desde un carácter y
espera 300 ms entre consultas; se cancelan búsquedas anteriores. No se usa un
catálogo Excel como reemplazo de una consulta real.

La captura del taller permite avanzar con **Enter** o **Tab** y retroceder con
**Shift+Enter** o **Shift+Tab**. Las flechas arriba/abajo mantienen la columna
entre filas; izquierda/derecha cambian de celda al llegar al límite del texto.
Dentro de un desplegable abierto las flechas recorren opciones y Enter
selecciona y avanza. Escape conserva cerrado el buscador aunque llegue una
respuesta pendiente. Enter al final de una fila con producto y cantidad crea
otra fila del mismo grupo; los valores calculados no reciben el foco.

Las cantidades y el precio de venta son editables. El costo promedio de los
insumos, la existencia a la fecha y la UM provienen exclusivamente del servidor.
Al validar, exportar e importar se consultan nuevamente en Siesa; se comprueba
el consumo acumulado por empresa, bodega, ítem y lote. La confirmación identifica
los datos consultados: si cambian antes de importar se exige validar otra vez.
Esta comprobación no reserva inventario; Siesa debe validar la disponibilidad
al contabilizar. No se reintentan importaciones automáticamente.

Se muestran costo, venta proyectada, utilidad, margen, costo de venta,
participación, merma y rendimiento. El reparto conserva las fórmulas de la hoja
TALLER del archivo de transformación: `costo / venta total`, costo unitario de
entrada `precio de venta * costo / venta total`, y margen
`(venta total - costo) / venta total`. Se permite un subproducto con precio cero
si la venta total de su transformación es positiva. Para comparar pesos y
calcular merma todos los movimientos deben usar la misma UM; no se inventan
conversiones. Una merma negativa se muestra como diferencia, sin ocultarla.

El consolidado permite editar o quitar transformaciones antes de enviar y
descargar un libro nuevo con **Hoja1**, **TALLER**, **CONSOLIDADO** y **BD**.
Hoja1 es reimportable por el flujo Excel; BD registra existencias, costos y
precios consultados, diferenciando el precio de venta editado. El original
`.xlsm` no se modifica y no se ejecutan ni se copian sus macros. El consolidado
es temporal en la pestaña; no hay historial persistente en base de datos.

#### Consultas REST para todas las compañías

El taller usa consultas GET contra
`https://apiconsulta.grupo-santacruz.com/carnes-frias`, enviando la compañía
seleccionada (`3`, `4`, `6`, `7` u `8`) en cada petición. La ruta conserva su
nombre por compatibilidad; no se sustituye la compañía seleccionada por la 8.
Con la clave de API configurada se usa REST para todas las compañías, sin
requerir plantillas SOAP de lectura. El navegador solo consulta al backend de EJECUTABLES; el token
se agrega a `X-API-Key` en el servidor y nunca se envía al navegador ni por URL.

**Integración multicompañía verificada el 23/11/2026:** el recorrido de centros,
bodegas, listas, productos, lotes y detalle devolvió HTTP 200 para las cinco
compañías a través del backend local y contra la API publicada, sin escrituras
en Siesa. El bloqueo previo a compañías distintas de la 8 quedó resuelto en
el servicio de consultas.

| Compañía | Centros activos | Listas vigentes |
| --- | --- | --- |
| 3 Agropecuaria | 3 | 38 |
| 4 Carnes Santacruz | 40 | 27 |
| 6 Cristian Serrano | 8 | 6 |
| 7 Inversiones Serueda | 5 | 3 |
| 8 Serrano Millán | 3 | 13 |

EJECUTABLES envía siempre `empresa` explícitamente, aunque la API conserve 8
como valor por defecto cuando no se recibe. Si una respuesta incluye
`empresa`, debe coincidir con la solicitada; cualquier discrepancia bloquea
la respuesta. La validación de captura vuelve a comprobar centros, bodegas,
lotes, costos y existencias de la compañía seleccionada. Un detalle con
`tiene_costo=false` o `tiene_precio=false` sigue indicando ausencia de datos,
no un cero válido. Estos conteos corresponden al momento de la verificación
y pueden cambiar con los catálogos de Siesa.

Configurar en **el contenedor de EJECUTABLES**, además del servidor de la API:

- `SIESA_CONSULTAS_API_KEY`: el mismo token autorizado por la API. Como
  alternativa se admite `API_KEY`; la variable específica tiene prioridad.
- `SIESA_CONSULTAS_BASE_URL`: opcional, por defecto
  `https://apiconsulta.grupo-santacruz.com`. El conector agrega `/carnes-frias`
  si no aparece al final. Tiene prioridad sobre el nombre anterior
  `SIESA_CONSULTAS_URL`, que sigue siendo compatible.
- `SIESA_CONSULTAS_TIMEOUT_MS`: espera de lectura en milisegundos; por defecto
  `30000` (30 segundos), con conexión limitada a 5 segundos. Acepta de 1 a
  300000. La URL debe usar HTTPS; no se siguen redirecciones con la clave.

En desarrollo la aplicación carga automáticamente el `.env` junto a `app.py`
antes de importar los conectores, sin sobrescribir variables ya presentes en
el entorno. Reiniciar el servidor después de cambiarlo. El archivo está
excluido de Git y del contexto de construcción de Docker; en contenedores se
inyectan las variables mediante Compose o el panel de despliegue.

Docker Compose pasa estas variables desde el entorno de despliegue. Una clave
configurada únicamente en el servicio de la API no está automáticamente
disponible en EJECUTABLES. No incluir el token en archivos versionados.

| Catálogo interno | Endpoint GET de la API |
| --- | --- |
| `centros` | `/centros-operacion` |
| `bodegas` | `/bodegas` |
| `listas` | `/listas-precios` |
| `productos` | `/productos` |
| `lotes` | `/lotes` |
| `detalle` | `/detalle-item` |

Los catálogos se leen de `data`; el detalle se recibe como objeto directo.
La existencia y el costo solo son exactos **hoy**, según la fecha de Colombia
(UTC-5). En la captura interactiva con REST se fija esa fecha y el
servidor rechaza otra fecha. La importación histórica por Excel no cambia.

`tiene_costo=false` bloquea el uso de un insumo: no se confunde el cero de
reemplazo con un costo real. Un producto terminado puede no tener costo previo
porque su costo se calcula desde los insumos. `tiene_precio=false` deja vacío
el precio del terminado y exige que el usuario lo ingrese explícitamente; el
servidor comprueba `precio_editado=true`. Un cero real con indicador `true`
sigue siendo válido, siempre que la venta total del taller sea positiva.

Se muestran `avisos` e `incluye_impuestos`. El precio se usa tal como lo devuelve
Siesa, sin inventar una tasa ni descontar impuestos; la utilidad es proyectada
sobre esa misma base. La UM del precio debe coincidir con la de inventario.

Los lotes de insumos se consultan con `solo_con_existencia=true`; los de destino,
con `false`, para incluir lotes activos sin saldo en la bodega. Se conserva
`maneja_lote`: si es verdadero se exige un lote activo incluso cuando la lista
está vacía. Si es falso no se acepta lote. La creación de lotes mediante el
conector 0403 **no está implementada**: crear antes el lote en Siesa; todos los
endpoints REST usados aquí siguen siendo de solo lectura. El envío SAI/EIN
conserva el conector de importación existente.

#### Compatibilidad con consultas SOAP de lectura

Si no se ha configurado clave de API y existen plantillas XML de consulta,
se conserva el proveedor SOAP. Con una clave configurada tiene prioridad REST
para cualquier compañía. No se usa SOAP como reemplazo silencioso cuando la
API rechaza una compañía.

El WSDL del servicio existente publica `EjecutarConsultaXML` con un parámetro
de texto `pvstrxmlParametros`. **El repositorio no incluye las definiciones XML
de consultas autorizadas para este tenant de Siesa.** No basta con conocer el
endpoint SOAP o las credenciales de importación. Hasta obtener y configurar
esas definiciones, la pantalla muestra **Conexión de lectura pendiente** y no
habilita el envío interactivo. La conexión real de lectura sigue pendiente de
verificación con el administrador de Siesa cuando se elige este proveedor.
Esta configuración no aplica al proveedor REST anterior.

Configurar en el entorno del servidor el XML interno completo autorizado para
cada una de estas variables. No es el sobre SOAP: la aplicación lo construye.
No se deben adivinar nombres de consultas, tablas ni el esquema del XML.

| Variable | Resultado esperado: alias de columnas |
| --- | --- |
| `SIESA_TALLER_XML_CENTROS` | `codigo`, `descripcion` |
| `SIESA_TALLER_XML_BODEGAS` | `codigo`, `descripcion` |
| `SIESA_TALLER_XML_LISTAS` | `codigo`, `descripcion` |
| `SIESA_TALLER_XML_PRODUCTOS` | `codigo`, `descripcion`, `referencia`, `um` |
| `SIESA_TALLER_XML_LOTES` | `codigo`, `descripcion` |
| `SIESA_TALLER_XML_DETALLE` | `codigo`, `descripcion`, `referencia`, `um`, `existencia`, `costo_promedio`, `precio_venta` |

Los alias pueden venir en mayúsculas o minúsculas. Cada fila debe ser un nodo
de DataSet con esas columnas como hijos directos. El detalle debe devolver
exactamente una fila del ítem solicitado; los números deben venir en formato
decimal sin separadores de miles. Una respuesta vacía, ambigua, sin precio o
sin costo no se reemplaza por cero. Un cero explícito sí es un dato válido.

Dentro de cada plantilla XML se reemplazan únicamente **textos completos de
elementos**, nunca SQL ni atributos, con estos marcadores:
`{conexion}`, `{usuario}`, `{clave}`, `{empresa}`, `{fecha}`, `{co}`, `{lista}`,
`{bodega}`, `{item}`, `{lote}` y `{q}`. Por ejemplo, un nodo de parámetro del
contrato autorizado puede tener como texto `{fecha}`. Los valores se escapan
mediante el serializador XML. Las credenciales permanecen en el servidor;
se usan `SIESA_USER`, `SIESA_PASSWORD` y la conexión compartida existente.

Requisitos de las consultas autorizadas:

- Filtrar siempre por compañía; bodegas además por centro seleccionado.
- Buscar productos por número de ítem o descripción usando `{q}` como
  **parámetro enlazado**, no concatenado en SQL. Filtrar antes de limitar
  resultados; la interfaz muestra hasta 40 coincidencias de producto.
- Filtrar lotes por ítem y bodega. Si el ítem no maneja lote, devolver cero
  filas; la selección vacía significa que no aplica lote, no todos los lotes.
- Resolver existencia y costo promedio para la fecha, bodega, ítem y lote
  solicitados, en la UM de inventario devuelta. No devolver una fila por
  ubicación, extensión u otra dimensión: agregar en Siesa según corresponda.
- Resolver precio por compañía, lista, ítem, UM y vigencia a la fecha.
- Devolver error o cero filas si falta el precio o costo; no usar `COALESCE`
  para convertir ausencia de información en un cero válido.
- Respetar los permisos del usuario técnico y no exponer credenciales en las
  columnas del resultado. Las definiciones de lectura deben ser de solo lectura.

La importación conserva los tipos SAI/EIN y requiere un número de taller válido;
verificar que no exista ya en Siesa. Antes de reintentar un envío con error o
respuesta incompleta, comprobar si Siesa recibió algún documento. La app sigue
sin autenticación propia: limitar el acceso en el proxy o portal antes de
habilitar las consultas y la importación en producción.

### Plantillas y limpieza

Las plantillas descargables están en [plantillas](./plantillas/). Los archivos
que estaban en la raíz siguen disponibles desde el botón de descarga de cada
proceso; no eran archivos sin uso. En la raíz se conserva `CODIGO SIESA.xlsx`,
catálogo FRIGOAPP → Siesa que varios procesadores necesitan en ejecución.

Los programas de la carpeta de entrega `nuevos_ejeuctables` se portaron a
`procesadores/taller.py`, `procesadores/siinv.py` e
`inventario_documentos.py`. La carpeta de entrega, sus ejecutables compilados,
archivos de depuración y copias auxiliares ya no son necesarios para la web.

### Documentos: Doc. Pedidos y Compromisos Pedidos

Estos dos procesos leen `ANALISIS.xlsx`, hoja `CANAL`, con encabezados en la
fila 7. Usan la misma empresa, fecha y selección de canales con cliente y
remisión. Buscan primero por `FECHA PEDIDO SIESA`; si no hay coincidencias,
buscan por `FECHA SACRIFICIO SIESA`.

- **Doc. Pedidos** genera un encabezado 430 por remisión y un movimiento 431
  por remisión/referencia, sumando los kilos de los canales de esa referencia.
- **Compromisos Pedidos** genera un registro 405 por canal. Cada registro conserva
  el `LOTE` completo de su misma fila (por ejemplo, `28746-473`) y apunta al
  número de movimiento 431 de su remisión/referencia. Varios ganchos pueden
  apuntar al mismo movimiento; el número de movimiento **no** es el gancho ni
  el consecutivo de fila del Excel.
- Ambos redondean los kilos por canal a dos decimales antes de sumar. La
  numeración de movimientos se comparte y no cambia al dividir el envío en lotes.
- Se rechazan lotes vacíos, sin formato lote-gancho o mayores de 15 caracteres:
  ya no se recortan. Si están diligenciados `GANCHO` o `LOTE FRIGOAPP`, deben
  coincidir con `LOTE` en esa misma fila; nunca se reconstruye usando otro canal.
- Se rechazan clientes/sucursales distintos en una remisión, o precios/fechas
  distintos dentro de una misma remisión/referencia, para no tomar silenciosamente
  el primer valor al agrupar. Corrige o separa esos pedidos antes de enviarlos.

Ejecuta primero **Doc. Pedidos** y después **Compromisos Pedidos**, con el mismo
archivo, empresa y fecha. No vuelvas a crear pedidos que ya existen sin
revisarlos en Siesa. Esta corrección no modifica documentos previamente cargados.

Pruebas locales, sin enviar a Siesa:

```powershell
python -m unittest discover -s tests -v
```

La prueba con el archivo de ejemplo completa los datos de pedido únicamente
en una copia temporal; no modifica `ANALISIS.xlsx`.

## Acceso

- **Desde SCTOOLS (recomendado)**: SCTOOLS -> Aplicaciones -> Ejecutables
- **URL directa**: `https://ejecutables.grupo-santacruz.com/` (producción)
- **Desarrollo local**: `http://localhost:5000`

**Nota**: No requiere autenticación SSO; cualquiera con acceso a la URL puede usarlo.

## Estructura

```
EJECUTABLES/
├── app.py                    # Servidor Flask (rutas y carga de archivos)
├── procesadores/
│   ├── __init__.py           # Registro de procesos
│   ├── siesa.py              # Lógica común: trama, XML y consumo SOAP
│   ├── pedidos.py
│   ├── requisiciones.py
│   └── sobrecostos.py
├── templates/index.html      # Interfaz (panel de navegación + carga)
├── plantillas/               # Plantillas Excel descargables de los procesos
├── static/css/styles.css     # Diseño (paleta blanco y verde)
├── static/js/app.js          # Lógica de la interfaz
├── docker-compose.yml        # Configuración Dokploy + Traefik
├── Dockerfile                # Build con Python 3.12 + gunicorn
├── deploy.ps1                # Script despliegue por SSH (PowerShell)
├── deploy.sh                 # Script configuración Traefik (Bash)
└── requirements.txt
```

Los archivos originales (`Pedidos.py`, `Requisiones.py`, `Sobrecostos.py`) se
conservan como referencia; la aplicación usa las versiones de `procesadores/`.

## Puesta en marcha

### Desarrollo local

```powershell
# 1. Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python app.py
# Acceso: http://localhost:5000
```

### Despliegue en Dokploy

1. Asegúrate de que las variables de entorno estén configuradas en Dokploy:
   - `EJECUTABLES_URL`: URL base de la app (ej: `https://ejecutables.grupo-santacruz.com`)
   - Cualquier credencial de Siesa necesaria

2. Ejecuta el script de despliegue (desde el servidor o localmente vía SSH):
   ```powershell
   ./deploy.ps1 -Server "usuario@servidor"
   ```

3. La app se desplegará en la red overlay `dokploy-network` con Traefik automático.

4. Actualiza el seeder de SCTOOLS si las URLs cambian (`.env` de SCTOOLS debe
   tener `EJECUTABLES_URL` configurado).


Abre `http://localhost:5000` en el navegador.

## Uso

1. En el panel lateral selecciona el proceso (Pedidos, Requisiciones o Sobrecostos).
2. Arrastra o selecciona el archivo Excel `PEDIDOS-SOBRECOSTOS.xlsx`.
3. Pulsa **Ejecutar proceso**. El resultado y la respuesta del servicio se
   muestran en pantalla.

## Seguridad (pendiente antes de producción)

Las credenciales del servicio web están definidas en cada procesador y pueden
sobrescribirse con variables de entorno:

```
SIESA_PEDIDOS_USER / SIESA_PEDIDOS_PASSWORD
SIESA_REQUISICIONES_USER / SIESA_REQUISICIONES_PASSWORD
SIESA_SOBRECOSTOS_USER / SIESA_SOBRECOSTOS_PASSWORD
```

Se recomienda **retirar las credenciales por defecto del código** y gestionarlas
solo por variables de entorno / gestor de secretos al integrar con el hub.

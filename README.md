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

Todos usan además las hojas `EQUIVALENTES` y `PARAMETROS`.

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

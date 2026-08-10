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

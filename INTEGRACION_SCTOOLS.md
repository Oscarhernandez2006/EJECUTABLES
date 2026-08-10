# Integración de EJECUTABLES en Suite SCTOOLS

## Resumen

EJECUTABLES ha sido registrado como una aplicación independiente en la Suite SCTOOLS. Aparecerá en el catálogo de aplicaciones del portal y será accesible desde el menú de SCTOOLS.

## Cambios realizados

### 1. Base de datos SCTOOLS

**Archivo**: `SCTOOLS/backend/database/seeders/ApplicationSeeder.php`

Se agregó una entrada para EJECUTABLES con los siguientes detalles:

```php
[
    'slug' => 'ejecutables',
    'name' => 'Ejecutables',
    'description' => 'Procesador de integraciones Siesa: carga y procesa archivos Excel (pedidos, requisiciones, sobrecostos)',
    'icon' => 'factory',
    'url' => env('EJECUTABLES_URL', 'http://localhost:5000'),
    'category' => 'Integraciones',
    'color' => '#8B5A8F',
    'logo' => null,
    'keywords' => 'siesa integraciones pedidos requisiciones sobrecostos excel',
    'type' => 'app',
    'sso_enabled' => false,
    'is_active' => true,
    'sort_order' => 5,
]
```

### 2. Variables de entorno SCTOOLS

**Archivo**: `SCTOOLS/backend/.env.example`

Se agregó:
```
EJECUTABLES_URL=http://localhost:5000
```

Asegúrate de que en el servidor de producción (.env real) esté configurado:
```
EJECUTABLES_URL=https://ejecutables.grupo-santacruz.com
```

### 3. Configuración Docker + Traefik

**Archivo nuevo**: `EJECUTABLES/docker-compose.yml`

Contiene la configuración completa para desplegar EJECUTABLES en Dokploy con Traefik:
- Red overlay: `dokploy-network`
- Puerto interno: 5000
- Dominio: `ejecutables.grupo-santacruz.com`
- Redirección HTTP -> HTTPS automática

### 4. Scripts de despliegue

**Archivo nuevo**: `EJECUTABLES/deploy.ps1`

Script PowerShell para desplegar EJECUTABLES por SSH a un servidor Ubuntu.

Uso:
```powershell
cd EJECUTABLES
./deploy.ps1 -Server "usuario@servidor" -Branch main
```

**Archivo nuevo**: `EJECUTABLES/deploy.sh`

Script Bash para configurar los labels de Traefik en Docker Swarm.
**Nota**: Reemplaza `ejecutables-ejecutables-XXXXX` con el ID real del servicio.

### 5. Documentación

**Archivo actualizado**: `EJECUTABLES/README.md`

Se agregó información sobre:
- Acceso desde SCTOOLS
- URL del portal
- Instrucciones de despliegue en Dokploy
- Configuración de variables de entorno

## Cómo usar

### Para usuarios finales

1. Inicia sesión en SCTOOLS: `https://sctools.grupo-santacruz.com`
2. Desde el portal, busca la app "Ejecutables" en el catálogo
3. Haz clic para acceder a EJECUTABLES
4. Carga un archivo Excel y procesa según el tipo de integración requerida

### Para desarrolladores

#### Desarrollo local

1. Asegúrate de que SCTOOLS tenga configurado en su `.env`:
   ```
   EJECUTABLES_URL=http://localhost:5000
   ```

2. Ejecuta EJECUTABLES en tu máquina:
   ```bash
   cd EJECUTABLES
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # o source .venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```

3. EJECUTABLES estará disponible en `http://localhost:5000`

4. Ejecuta los seeders de SCTOOLS para actualizar la BD:
   ```bash
   cd SCTOOLS/backend
   php artisan migrate
   php artisan db:seed --class=ApplicationSeeder
   ```

5. El catálogo de SCTOOLS incluirá EJECUTABLES automáticamente.

#### Despliegue en producción

1. Asegúrate de que `.env` de SCTOOLS tenga:
   ```
   EJECUTABLES_URL=https://ejecutables.grupo-santacruz.com
   ```

2. Ejecuta el script de despliegue desde tu máquina:
   ```powershell
   cd EJECUTABLES
   ./deploy.ps1 -Server "usuario@servidor" -Branch main
   ```

3. El script:
   - Clona/actualiza el código del repositorio
   - Construye la imagen Docker
   - Despliega EJECUTABLES en Dokploy
   - Configura Traefik automáticamente

4. Acceso:
   - URL: `https://ejecutables.grupo-santacruz.com`
   - Desde SCTOOLS: Portal -> Ejecutables

## Permisos y acceso

EJECUTABLES **no requiere autenticación SSO**, por lo que es accesible directamente por URL sin pasar por SCTOOLS.

Sin embargo, está registrado en el catálogo de SCTOOLS para facilitar el descubrimiento y acceso centralizado.

Los permisos de acceso se pueden gestionar desde SCTOOLS -> Administración -> Permisos, aunque por defecto todos los usuarios autenticados tienen acceso.

## Troubleshooting

### EJECUTABLES no aparece en el catálogo de SCTOOLS

1. Verifica que los seeders se hayan ejecutado:
   ```bash
   php artisan db:seed --class=ApplicationSeeder
   ```

2. Comprueba que `EJECUTABLES_URL` esté definido en `.env` de SCTOOLS

3. Recarga la página de SCTOOLS en el navegador (Ctrl+Shift+R para limpiar caché)

### EJECUTABLES no es accesible desde SCTOOLS

1. Verifica que EJECUTABLES esté corriendo en el puerto correcto
2. Comprueba la URL en la BD: `SELECT * FROM applications WHERE slug = 'ejecutables';`
3. Verifica que Traefik tenga el dominio correctamente configurado

### Error CORS al intentar comunicación entre apps

Aunque EJECUTABLES no lo requiere actualmente, si necesitas agregar CORS:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://sctools.grupo-santacruz.com", "http://localhost:5173"])
```

Agrega `flask-cors` a `requirements.txt`:
```
flask-cors==4.0.0
```

## Variables de entorno recomendadas (Dokploy)

Configura en Dokploy las siguientes variables para EJECUTABLES:

```
PORT=5000
FLASK_ENV=production

# Opcional: credenciales de Siesa si EJECUTABLES las necesita
# SIESA_URL=...
# SIESA_USER=...
# SIESA_PASSWORD=...
```

## Notas

- EJECUTABLES corre en Python 3.12 con gunicorn (timeout: 180s para permitir procesos largos de Siesa)
- Soporta archivos Excel hasta 25 MB
- Los procesos ejecutados se registran en los logs del contenedor
- El build de la imagen Docker está optimizado con caché de capas

## Contacto y soporte

Para cambios en la integración con SCTOOLS o problemas de despliegue, coordina con el equipo DevOps.

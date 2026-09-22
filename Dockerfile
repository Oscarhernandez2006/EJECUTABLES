# Imagen base con Python (los wheels de pandas/numpy están precompilados aquí).
FROM python:3.12-slim

# Buenas prácticas de entorno.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Instalar dependencias primero (mejor uso de la caché de capas).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto.
COPY . .

EXPOSE 5000

# Servidor WSGI de producción.
# timeout alto porque el consumo del servicio SOAP de Siesa puede tardar.
# access-logfile "-" -> log a stdout con método, ruta y status HTTP (200/400/404/500...) de cada petición.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 180 --access-logfile - --access-logformat '%(h)s \"%(r)s\" %(s)s %(b)s %(D)sus' app:app"]

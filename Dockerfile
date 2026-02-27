FROM python:3.12-slim

WORKDIR /app

# requirements.txt va primero para aprovechar el cache de Docker.
# Si solo cambiás código Python, no se reinstalan las dependencias.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Recién acá copiamos el código, después del install.
COPY . .

# Cada servicio define su propio comando en docker-compose.yml.
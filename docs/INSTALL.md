# Instalación y puesta en marcha

## Requisitos previos

- Python 3.10 o superior
- MariaDB 10.6 o superior
- Redis 7.0 o superior
- Git

## 1. Clonar el repositorio

    git clone https://github.com/TU_USUARIO/PharmaNotify.git
    cd pharma-notifications

## 2. Crear y activar el entorno virtual

    python3 -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate

## 3. Instalar las dependencias Python

    pip install -r rrequirements.txt

## 4. Configurar MariaDB

Primero asegurate de que el servicio esté corriendo:

    sudo systemctl start mariadb

Luego entrá a MariaDB como root y creá la base de datos y el usuario:

    sudo mysql -u root -p

Una vez dentro del prompt de MariaDB, ejecutá:

    CREATE DATABASE pharma_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'pharma_user'@'localhost' IDENTIFIED BY 'pharma_pass';
    GRANT ALL PRIVILEGES ON pharma_db.* TO 'pharma_user'@'localhost';
    FLUSH PRIVILEGES;
    EXIT;

Finalmente, inicializá las tablas:

    mysql -u pharma_user -p pharma_db < final/scripts/init_db.sql

## 5. Configurar Redis

    sudo systemctl start redis-server

Verificá que está corriendo:

    redis-cli ping
    # Debe responder: PONG

## 6. Verificar la configuración

Revisá `src/config.py` y confirmá que los valores coinciden con tu entorno
(host, puerto, credenciales de base de datos). Los valores por defecto deberían
funcionar si seguiste los pasos anteriores sin modificaciones.

## 7. Iniciar el sistema

Cada componente se ejecuta en una terminal separada.

**Terminal 1 — Servidor:**

    cd src/
    python server.py --port 9999

**Terminal 2 — Worker de Celery:**

    cd src/
    celery -A celery_app worker --loglevel=info

**Terminal 3 — Celery Beat (tareas periódicas):**

    cd src/
    celery -A celery_app beat --loglevel=info

**Terminal 4 — Cliente (una por farmacia):**

    cd src/
    python client.py --host localhost --port 9999 --farmacia "Farmacia Central"

**Terminal 5 — Monitor (opcional):**

    cd src/
    python monitor.py --socket /tmp/pharma_monitor.sock
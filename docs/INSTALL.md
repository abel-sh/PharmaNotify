# Instalación y puesta en marcha

Hay dos caminos para instalar PharmaNotify: con **Docker** o en **entorno local**. Docker es la opción recomendada porque levanta todo el sistema con un único comando sin necesidad de instalar ni configurar MariaDB y Redis manualmente. El entorno local es útil si preferís tener control directo sobre cada componente o si estás trabajando en el código.

---

## Opción A — Docker (recomendado)

### Requisitos previos

- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/) (viene incluido con Docker Desktop; en Linux instalarlo como plugin con `docker compose`)

### 1. Clonar el repositorio

```bash
git clone https://github.com/abel-sh/PharmaNotify.git
cd PharmaNotify
```

### 2. Configurar las variables de entorno

```bash
cp .env.example .env
```

Los valores por defecto del `.env.example` funcionan para un entorno de desarrollo sin modificaciones. Si querés cambiar credenciales o puertos, editá el `.env` antes de continuar.

### 3. Levantar el sistema

```bash
docker compose up -d
```

Este comando construye la imagen Python, descarga las imágenes de MariaDB y Redis, inicializa las tablas automáticamente, y levanta todos los servicios en segundo plano. La primera vez tarda unos minutos porque descarga las imágenes base.

Podés verificar que todos los servicios estén corriendo con:

```bash
docker compose ps
```

Los servicios `mariadb` y `redis` deben aparecer como `healthy`, y `server`, `celery-worker` y `celery-beat` como `running`.

### 4. Usar el sistema

Para abrir el monitor administrativo (registrar farmacias, ver estadísticas):

```bash
docker compose run --rm monitor
```

Argumento opcional: `--socket` (ruta del Unix Domain Socket, por defecto `/tmp/pharma_monitor.sock`).

Para conectar una farmacia (la farmacia debe estar registrada primero desde el monitor):

```bash
docker compose run --rm client --farmacia "Nombre de la farmacia"
```

Argumentos opcionales: `--host` (por defecto `localhost`) y `--puerto` (por defecto 9999).

### 5. Apagar el sistema

Para apagar los servicios conservando los datos de la base de datos:

```bash
docker compose down
```

Para apagar y borrar también los datos (empezar desde cero):

```bash
docker compose down -v
```

---

## Opción B — Entorno local

### Requisitos previos

- Python 3.10 o superior
- MariaDB 10.6 o superior
- Redis 7.0 o superior
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/PharmaNotify.git
cd PharmaNotify
```

### 2. Crear y activar el entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar las dependencias Python

```bash
pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

```bash
cp .env.example .env
```

Los valores por defecto funcionan si seguís los pasos de configuración de MariaDB y Redis sin modificar credenciales ni puertos.

### 5. Configurar MariaDB

Asegurate de que el servicio esté corriendo:

```bash
sudo systemctl start mariadb
```

Entrá como root y creá la base de datos y el usuario de la aplicación:

```bash
sudo mysql -u root -p
```

Una vez dentro del prompt de MariaDB ejecutá:

```sql
CREATE DATABASE pharma_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pharma_user'@'localhost' IDENTIFIED BY 'pharma_pass';
GRANT ALL PRIVILEGES ON pharma_db.* TO 'pharma_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Inicializá las tablas con el script incluido en el proyecto:

```bash
bash scripts/init_db.sh
```

### 6. Configurar Redis

```bash
sudo systemctl start redis-server
```

Verificá que está respondiendo:

```bash
redis-cli ping
# Debe responder: PONG
```

### 7. Iniciar el sistema

Cada componente se ejecuta en una terminal separada, desde la raíz del proyecto.

**Terminal 1 — Servidor:**

```bash
python -m src.server.server
```

Argumentos opcionales: `--host` (interfaz donde escuchar, por defecto todas) y `--puerto` (por defecto 9999).

**Terminal 2 — Worker de Celery:**

```bash
celery -A src.workers.celery_app worker --loglevel=info
```

**Terminal 3 — Celery Beat (tareas periódicas):**

```bash
celery -A src.workers.celery_app beat --loglevel=info
```

**Terminal 4 — Monitor (administrador):**

```bash
python -m src.monitor.monitor
```

Argumento opcional: `--socket` (ruta del Unix Domain Socket, por defecto `/tmp/pharma_monitor.sock`).

**Terminal 5 — Cliente (una por farmacia):**

```bash
python -m src.client.client --farmacia "Nombre de la farmacia"
```

Argumentos opcionales: `--host` (por defecto `localhost`) y `--puerto` (por defecto 9999).
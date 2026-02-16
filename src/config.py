import os
from dotenv import load_dotenv

# load_dotenv() busca el archivo .env y carga sus variables.
# Con este path explícito siempre lo encuentra sin importar desde dónde se ejecute el programa.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# =============================================================================
# Servidor TCP
# =============================================================================
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT  = int(os.getenv("SERVER_PORT", 9999))  # int() porque getenv devuelve strings

MONITOR_SOCKET_PATH = os.getenv("MONITOR_SOCKET_PATH", "/tmp/pharma_monitor.sock")

# =============================================================================
# MariaDB
# =============================================================================
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_NAME     = os.getenv("DB_NAME", "pharma_db")
DB_USER     = os.getenv("DB_USER", "pharma_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "pharma_pass")

# =============================================================================
# Redis
# =============================================================================
REDIS_HOST    = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT    = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB      = int(os.getenv("REDIS_DB", 0)) # Redis no tiene bases de datos con nombres como MariaDB, sino que tiene bases de datos numeradas del 0 al 15. El 0 es el que se usa por defecto.
REDIS_URL     = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
REDIS_NOTIFICATIONS_CHANNEL = os.getenv("REDIS_NOTIFICATIONS_CHANNEL", "pharma:notifications")

# =============================================================================
# Celery
# =============================================================================
CELERY_BROKER_URL      = REDIS_URL
CELERY_RESULT_BACKEND  = REDIS_URL # Dónde guardar los resultados de las tareas ejecutadas
VERIFICATION_INTERVAL_SECONDS = int(os.getenv("VERIFICATION_INTERVAL_SECONDS", 60))

# =============================================================================
# Notificaciones
# =============================================================================
DEFAULT_ALERT_THRESHOLD_DAYS = int(os.getenv("DEFAULT_ALERT_THRESHOLD_DAYS", 7)) # Umbral por defecto de días de anticipación para generar alertas de vencimient
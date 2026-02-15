# =============================================================================
# Configuración del Servidor TCP
# =============================================================================
SERVER_HOST = "localhost"
SERVER_PORT = 9999

# Ruta del Unix Domain Socket para la comunicación con el monitor (IPC)
MONITOR_SOCKET_PATH = "/tmp/pharma_monitor.sock"

# =============================================================================
# Configuración de MariaDB
# =============================================================================
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "pharma_db"
DB_USER = "pharma_user"
DB_PASSWORD = "pharma_pass"

# =============================================================================
# Configuración de Redis
# =============================================================================
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0  # Redis maneja múltiples bases de datos numeradas, usamos la 0

# URL completa de Redis, que es el formato que necesita Celery como broker
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Canal pub/sub donde los workers publican notificaciones
# El servidor estará suscrito a este canal
REDIS_NOTIFICATIONS_CHANNEL = "pharma:notifications"

# =============================================================================
# Configuración de Celery
# =============================================================================
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Cada cuántos segundos Celery Beat verifica los vencimientos
VERIFICATION_INTERVAL_SECONDS = 60

# =============================================================================
# Configuración de notificaciones por defecto
# =============================================================================
# Días de anticipación para notificar sobre medicamentos próximos a vencer
DEFAULT_ALERT_THRESHOLD_DAYS = 7
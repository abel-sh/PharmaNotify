"""
Módulo compartido con configuraciones y utilidades usadas por todos los componentes.
"""

# Exponemos las configuraciones más usadas
from .config import (
    SERVER_LISTEN_HOST,
    SERVER_CONNECT_HOST,
    SERVER_PORT,
    MONITOR_SOCKET_PATH,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_NOTIFICATIONS_CHANNEL,
    DEFAULT_ALERT_THRESHOLD_DAYS
)

# Exponemos la función para obtener loggers configurados
from .logger import obtener_logger  

# Exponemos las funciones del protocolo de comunicación
from .protocol import (
    enviar_mensaje,
    recibir_mensaje
)

__all__ = [
    'SERVER_LISTEN_HOST', 'SERVER_CONNECT_HOST', 'SERVER_PORT',
    'MONITOR_SOCKET_PATH',
    'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
    'REDIS_HOST', 'REDIS_PORT', 'REDIS_DB', 'REDIS_NOTIFICATIONS_CHANNEL',
    'DEFAULT_ALERT_THRESHOLD_DAYS',
    'obtener_logger',
    'enviar_mensaje', 'recibir_mensaje'
]
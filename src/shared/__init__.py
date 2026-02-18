"""
Módulo compartido con configuraciones y utilidades usadas por todos los componentes.
"""

# Exponemos las configuraciones más usadas
from .config import (
    SERVER_HOST,
    SERVER_PORT,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_NOTIFICATIONS_CHANNEL,
    DEFAULT_ALERT_THRESHOLD_DAYS
)

__all__ = [
    'SERVER_HOST', 'SERVER_PORT',
    'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
    'REDIS_HOST', 'REDIS_PORT', 'REDIS_NOTIFICATIONS_CHANNEL',
    'DEFAULT_ALERT_THRESHOLD_DAYS',
]
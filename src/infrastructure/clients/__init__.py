"""
Clientes de servicios externos.
Centraliza la creación de conexiones para que el resto del sistema
no sepa ni le importe qué motor de BD o broker se está usando.
"""

from src.infrastructure.clients.database import get_async_connection, get_sync_connection
from src.infrastructure.clients.redis import get_redis_client, get_async_redis_client

__all__ = [
    "get_async_connection",
    "get_sync_connection",
    "get_redis_client",
    "get_async_redis_client",
]
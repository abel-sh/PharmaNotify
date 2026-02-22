"""
Cliente de Redis.
Provee conexiones sync (para workers Celery) y async (para el servidor AsyncIO).
Centralizar la creación aquí significa que si Redis cambia de host, puerto,
o se reemplaza por otro broker, el cambio ocurre en un único lugar.
"""

import redis
import redis.asyncio as aioredis
from src.shared.config import REDIS_HOST, REDIS_PORT, REDIS_DB


def get_redis_client() -> redis.Redis:
    """
    Cliente Redis sincrónico para los workers de Celery.
    Usado para publicar notificaciones en el canal pub/sub.
    """
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


def get_async_redis_client() -> aioredis.Redis:
    """
    Cliente Redis asíncrono para el servidor AsyncIO.
    Usado para suscribirse al canal pub/sub sin bloquear el event loop.
    """
    return aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
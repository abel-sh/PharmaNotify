"""
Paquete de infraestructura de PharmaNotify.

Estructura interna:
  clients/      → conexiones a servicios externos (MariaDB, Redis)
  repositories/ → operaciones de datos por entidad del dominio

Todo se re-exporta desde aquí para que el resto del sistema
importe desde src.infrastructure sin conocer la estructura interna.
Si en el futuro se reorganiza internamente, los imports externos no se rompen.
"""

from src.infrastructure.clients import (
    get_async_connection,
    get_sync_connection,
    get_redis_client,
    get_async_redis_client,
)
from src.infrastructure.repositories import (
    crear_medicamento,
    listar_medicamentos,
    buscar_medicamento,
    actualizar_medicamento,
    eliminar_medicamento,
    guardar_notificacion,
    guardar_notificacion_sync,
    ver_notificaciones,
    configurar_umbral,
    verificar_notificacion_reciente_sync,
    limpiar_notificaciones_antiguas_sync
)

__all__ = [
    "get_async_connection",
    "get_sync_connection",
    "get_redis_client",
    "get_async_redis_client",
    "crear_medicamento",
    "listar_medicamentos",
    "buscar_medicamento",
    "actualizar_medicamento",
    "eliminar_medicamento",
    "guardar_notificacion",
    "guardar_notificacion_sync",
    "ver_notificaciones",
    "configurar_umbral",
    "verificar_notificacion_reciente_sync",
    "limpiar_notificaciones_antiguas_sync"
]
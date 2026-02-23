"""
Repositorios de acceso a datos.
Cada módulo encapsula las operaciones de una entidad del dominio.
Usan los clientes de infrastructure/clients/ para conectarse,
pero no saben ni les importa cómo se crean esas conexiones.
"""

from src.infrastructure.repositories.medicamentos import (
    crear_medicamento,
    listar_medicamentos,
    buscar_medicamento,
    actualizar_medicamento,
    eliminar_medicamento,
)
from src.infrastructure.repositories.notificaciones import (
    guardar_notificacion,
    guardar_notificacion_sync,
    ver_notificaciones,
    verificar_notificacion_reciente_sync,
    limpiar_notificaciones_antiguas_sync
)
from src.infrastructure.repositories.farmacias import configurar_umbral

__all__ = [
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
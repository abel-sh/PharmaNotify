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
    ver_notificaciones,
)

from src.infrastructure.repositories.notificaciones_sync import (
    guardar_notificacion_sync,
    verificar_notificacion_reciente_sync,
    obtener_medicamentos_proximos_sync,
    limpiar_notificaciones_antiguas_sync
)

from src.infrastructure.repositories.farmacias import (
    crear_farmacia,
    listar_farmacias,
    renombrar_farmacia,
    buscar_farmacia_por_nombre,
    activar_farmacia,
    desactivar_farmacia,
    configurar_umbral,
    obtener_estadisticas,
    obtener_resumen_farmacia
)

__all__ = [
    "crear_medicamento",
    "listar_medicamentos",
    "buscar_medicamento",
    "actualizar_medicamento",
    "eliminar_medicamento",
    "guardar_notificacion",
    "guardar_notificacion_sync",
    "ver_notificaciones",
    "verificar_notificacion_reciente_sync",
    "obtener_medicamentos_proximos_sync",
    "limpiar_notificaciones_antiguas_sync",
    "crear_farmacia",
    "listar_farmacias",
    "renombrar_farmacia",
    "buscar_farmacia_por_nombre",
    "activar_farmacia",
    "desactivar_farmacia",
    "configurar_umbral",
    "obtener_estadisticas",
    "obtener_resumen_farmacia"
]
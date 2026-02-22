"""
Módulo de acceso a datos.
Expone las funciones de conexión y operaciones con MariaDB.

Estructura interna:
  connection.py    → funciones de conexión a MariaDB (async y sync)
  medicamentos.py  → CRUD de medicamentos
  notificaciones.py → operaciones de notificaciones
  farmacias.py     → operaciones sobre farmacias
"""

from src.infrastructure.connection import get_async_connection, get_sync_connection

from src.infrastructure.medicamentos import (
    crear_medicamento,
    listar_medicamentos,
    buscar_medicamento,
    actualizar_medicamento,
    eliminar_medicamento,
)
from src.infrastructure.notificaciones import (
    guardar_notificacion,
    guardar_notificacion_sync,
    ver_notificaciones,
)
from src.infrastructure.farmacias import configurar_umbral

__all__ = [
    "get_async_connection",
    "get_sync_connection",
    "crear_medicamento",
    "listar_medicamentos",
    "buscar_medicamento",
    "actualizar_medicamento",
    "eliminar_medicamento",
    "guardar_notificacion",
    "guardar_notificacion_sync",
    "ver_notificaciones",
    "configurar_umbral",
]
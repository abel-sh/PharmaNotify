"""
Módulo de acceso a datos.
Expone las funciones de conexión y operaciones con MariaDB.
"""

# Importamos las funciones que queremos exponer públicamente
from .database import (
    get_async_connection,
    get_sync_connection,
    crear_medicamento,
    listar_medicamentos,
    buscar_medicamento,
    actualizar_medicamento,
    eliminar_medicamento
)

# Esto define qué se importa cuando alguien hace "from db import *"
__all__ = [
    'get_async_connection',
    'get_sync_connection',
    'crear_medicamento',
    'listar_medicamentos',
    'buscar_medicamento',
    'actualizar_medicamento',
    'eliminar_medicamento'
]
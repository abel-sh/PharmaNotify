"""
Módulo de acceso a datos.
Expone las funciones de conexión y operaciones con MariaDB.
"""

# Importamos las funciones que queremos exponer públicamente
from .database import (
    get_async_connection,
    get_sync_connection
)

# Esto define qué se importa cuando alguien hace "from db import *"
__all__ = [
    'get_async_connection',
    'get_sync_connection',
]
import aiomysql
import pymysql
from src.shared import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


# =============================================================================
# Conexión ASYNC — para el servidor AsyncIO
# =============================================================================

async def get_async_connection():
    """
    Devuelve una conexión async a MariaDB.
    Usada por el servidor para no bloquear el event loop mientras espera la BD.
    """
    conexion = await aiomysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        autocommit=True
    )
    return conexion


# =============================================================================
# Conexión SYNC — para los workers de Celery
# =============================================================================

def get_sync_connection():
    """
    Devuelve una conexión sync a MariaDB.
    Usada por los workers de Celery, que no corren en un event loop.
    """
    conexion = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True
    )
    return conexion
import aiomysql
import pymysql
from src.shared.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


async def get_async_connection():
    """
    Conexión async a MariaDB para el servidor AsyncIO.
    Usar aiomysql evita bloquear el event loop mientras espera respuesta de la BD.
    """
    return await aiomysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        autocommit=True
    )


def get_sync_connection():
    """
    Conexión sync a MariaDB para los workers de Celery.
    Los workers no tienen event loop, por eso usan pymysql directamente.
    """
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True
    )
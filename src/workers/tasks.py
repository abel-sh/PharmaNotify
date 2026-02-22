import json
import redis
from src.workers.celery_app import celery_app
from src.shared.logger import obtener_logger
from src.shared.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_NOTIFICATIONS_CHANNEL
from src.infrastructure.connection import get_sync_connection
from src.infrastructure.notificaciones import guardar_notificacion_sync

logger = obtener_logger("worker")


@celery_app.task(bind=True)
def tarea_de_prueba(self):
    """
    Tarea de verificación del sistema. Se reemplazará en el Issue #9.
    """
    logger.info(
        f"[task_id={self.request.id}] "
        f"Tarea de prueba ejecutada correctamente."
    )
    return "ok"


@celery_app.task(bind=True)
def notificar_evento(self, farmacia_id: int, tipo: str, mensaje: str):
    """
    Tarea disparada por el servidor después de cada operación CRUD.

    Tiene dos responsabilidades:
      1. Persistir la notificación en la BD (para el historial).
      2. Publicarla en el canal Redis (para entregarla en tiempo real
         al cliente conectado, si lo hay).

    La separación entre persistencia y entrega en tiempo real es intencional:
    si la farmacia no está conectada cuando ocurre el evento, igual queda
    un registro en la BD que podrá consultar cuando vuelva a conectarse.
    """
    conn = None
    try:
        # Persistencia: guardamos la notificación en la BD
        # usando la conexión sync porque los workers no tienen event loop.
        conn = get_sync_connection()
        guardar_notificacion_sync(conn, farmacia_id, tipo, mensaje)
        logger.info(
            f"[task_id={self.request.id}] "
            f"Notificación persistida para farmacia_id={farmacia_id}: {tipo}"
        )

        # Publicación en Redis pub/sub.
        # Creamos una conexión Redis separada de la que usa Celery como broker.
        cliente_redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

        # El mensaje que publicamos es un JSON con toda la información
        # necesaria para que el servidor sepa a quién enviarle la notificación
        # y qué mostrarle.
        payload = json.dumps({
            "farmacia_id": farmacia_id,
            "tipo": "notificacion",
            "mensaje": mensaje
        }, ensure_ascii=False)

        # publish() devuelve el número de suscriptores que recibieron el mensaje.
        # Si es 0, el servidor no estaba suscrito (o no había clientes conectados),
        # pero igual está guardado en la BD para consulta posterior.
        suscriptores = cliente_redis.publish(REDIS_NOTIFICATIONS_CHANNEL, payload)
        logger.info(
            f"[task_id={self.request.id}] "
            f"Notificación publicada en Redis. Suscriptores activos: {suscriptores}"
        )

    except Exception as e:
        logger.error(
            f"[task_id={self.request.id}] "
            f"Error en notificar_evento para farmacia_id={farmacia_id}: {e}"
        )
        # retry() reintenta la tarea automáticamente después de 5 segundos,
        # hasta un máximo de 3 intentos. Útil si Redis o la BD están
        # temporalmente no disponibles.
        raise self.retry(exc=e, countdown=5, max_retries=3)

    finally:
        if conn:
            conn.close()
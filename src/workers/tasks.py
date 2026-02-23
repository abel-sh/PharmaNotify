import json
from src.workers.celery_app import celery_app
from src.shared.logger import obtener_logger
from src.shared.config import REDIS_NOTIFICATIONS_CHANNEL, NOTIFICATION_RETENTION_DAYS
from src.infrastructure import (
    get_sync_connection,
    get_redis_client,
    guardar_notificacion_sync,
    verificar_notificacion_reciente_sync,
    limpiar_notificaciones_antiguas_sync
)

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
        cliente_redis = get_redis_client()

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
            

@celery_app.task(bind=True)
def verificar_vencimientos(self):
    """Detecta medicamentos próximos a vencer y genera alertas."""
    conn = None
    try:
        conn = get_sync_connection()
        cliente_redis = get_redis_client()

        with conn.cursor() as cursor:
            # JOIN con farmacias para usar el umbral_dias de cada una.
            # Excluimos fecha_vencimiento < CURDATE() porque esos los manejaré luego
            cursor.execute(
                """
                SELECT
                    m.farmacia_id,
                    m.codigo,
                    m.nombre,
                    m.fecha_vencimiento,
                    f.umbral_dias,
                    DATEDIFF(m.fecha_vencimiento, CURDATE()) AS dias_restantes
                FROM medicamentos m
                JOIN farmacias f ON f.id = m.farmacia_id
                WHERE m.activo = TRUE
                  AND f.activo = TRUE
                  AND m.fecha_vencimiento <= DATE_ADD(CURDATE(), INTERVAL f.umbral_dias DAY)
                  AND m.fecha_vencimiento >= CURDATE()
                ORDER BY m.fecha_vencimiento ASC
                """
            )
            medicamentos_proximos = cursor.fetchall()

        logger.info(
            f"[task_id={self.request.id}] "
            f"verificar_vencimientos: {len(medicamentos_proximos)} medicamento(s) dentro del umbral."
        )

        for fila in medicamentos_proximos:
            farmacia_id, codigo, nombre, fecha_venc, umbral_dias, dias_restantes = fila

            # Anti-duplicados: máximo una alerta por medicamento por día.
            if verificar_notificacion_reciente_sync(conn, farmacia_id, codigo):
                logger.info(
                    f"[task_id={self.request.id}] "
                    f"Duplicado omitido: '{codigo}' farmacia_id={farmacia_id}."
                )
                continue

            if dias_restantes == 0:
                aviso_dias = "vence HOY"
            elif dias_restantes == 1:
                aviso_dias = "vence mañana"
            else:
                aviso_dias = f"vence en {dias_restantes} días"

            mensaje = f"⚠ ALERTA: '{nombre}' (código: {codigo}) {aviso_dias} ({fecha_venc})."

            guardar_notificacion_sync(conn, farmacia_id, "proximo_vencimiento", mensaje)

            payload = json.dumps({
                "farmacia_id": farmacia_id,
                "tipo": "notificacion",
                "mensaje": mensaje
            }, ensure_ascii=False)
            cliente_redis.publish(REDIS_NOTIFICATIONS_CHANNEL, payload)

            # WARNING: situación que requiere atención humana, no un error del sistema.
            logger.warning(
                f"[task_id={self.request.id}] "
                f"ALERTA: '{nombre}' (código: {codigo}) "
                f"farmacia_id={farmacia_id}, dias_restantes={dias_restantes}."
            )

    except Exception as e:
        logger.error(f"[task_id={self.request.id}] Error en verificar_vencimientos: {e}")
        raise self.retry(exc=e, countdown=10, max_retries=3)

    finally:
        if conn:
            conn.close()
            

@celery_app.task(bind=True)
def limpiar_notificaciones_antiguas(self):
    """
    Tarea periódica que elimina físicamente notificaciones leídas
    con más de NOTIFICATION_RETENTION_DAYS días de antigüedad.

    Se ejecuta una vez por día a las 3 AM usando crontab, momento
    de baja actividad para minimizar el impacto en la BD.

    A diferencia del resto del sistema que usa eliminación lógica,
    acá la eliminación es física porque las notificaciones viejas
    y leídas ya no tienen valor histórico que preservar.
    """
    conn = None
    try:
        conn = get_sync_connection()
        eliminadas = limpiar_notificaciones_antiguas_sync(conn, NOTIFICATION_RETENTION_DAYS)

        # INFO porque es una operación de mantenimiento rutinaria,
        # no una situación que requiera atención humana.
        logger.info(
            f"[task_id={self.request.id}] "
            f"limpiar_notificaciones_antiguas: {eliminadas} notificación(es) "
            f"eliminada(s) (retención: {NOTIFICATION_RETENTION_DAYS} días)."
        )

    except Exception as e:
        logger.error(
            f"[task_id={self.request.id}] "
            f"Error en limpiar_notificaciones_antiguas: {e}"
        )
        raise self.retry(exc=e, countdown=60, max_retries=3)

    finally:
        if conn:
            conn.close()
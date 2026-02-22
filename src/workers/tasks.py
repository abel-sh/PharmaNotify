from src.workers.celery_app import celery_app
from src.shared.logger import obtener_logger

# Usamos el logger centralizado del sistema en lugar de print(), igual que en el servidor
logger = obtener_logger("worker")

# El decorador @celery_app.task es lo que transforma una función Python normal
# en una "tarea Celery". Sin él, sería solo una función. Con él, Celery sabe
# que puede:

# bind=True hace que el primer parámetro "self" sea la propia instancia
# de la tarea. Esto permite acceder a metadata como self.request.id
# (el ID único de esta ejecución) y hacer cosas como reintentos: self.retry().

@celery_app.task(bind=True)
def tarea_de_prueba(self):
    """
    Tarea de verificación del sistema.
    Se ejecuta periódicamente según VERIFICATION_INTERVAL_SECONDS.
    Su único propósito es confirmar que Celery + Redis están operativos..
    """
    logger.info(
        f"[task_id={self.request.id}] "
        f"Tarea de prueba ejecutada correctamente. "
        f"El sistema Celery está operativo."
    )
    # Devolvemos un string descriptivo para que aparezca en el result backend
    return "ok"
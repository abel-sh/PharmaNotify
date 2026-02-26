"""
Configuración de la instancia Celery y del scheduler Beat.

Define la conexión al broker Redis, el autodiscovery de tareas
en src.workers.tasks, y la programación de tareas periódicas:
  - verificar_vencimientos: cada VERIFICATION_INTERVAL_SECONDS segundos.
  - limpiar_notificaciones_antiguas: una vez por día a las 3 AM.
"""

from celery import Celery
from celery.schedules import crontab

from src.shared.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    VERIFICATION_INTERVAL_SECONDS
)

# Instancia principal de Celery
celery_app = Celery("pharma_notify")

# Configuración
celery_app.conf.update(
    # El broker es el intermediario que recibe y almacena las tareas
    broker_url=CELERY_BROKER_URL,

    # Resultados donde Celery guarda los resultados de las tareas ejecutadas.
    result_backend=CELERY_RESULT_BACKEND,

    # timezone asegura que Celery Beat maneje correctamente
    timezone="America/Argentina/Buenos_Aires",

    # autodiscover_tasks es equivalente a decirle a Celery:
    # "buscá automáticamente archivos tasks.py dentro de estos paquetes".
    include=["src.workers.tasks"],

    # Indica dónde Beat debe guardar su archivo de estado.
    beat_schedule_filename="/tmp/celerybeat-schedule",
)


# Celery Beat: el programador de tareas periódicas

# beat_schedule define qué tareas se ejecutan automáticamente y cada cuánto.
# Cada entrada del diccionario es una tarea programada con tres partes:
#   "task":     el nombre completo de la función de tarea a ejecutar
#   "schedule": cada cuánto tiempo ejecutarla (en segundos, o con crontab)
#   "args":     argumentos que se le pasan a la tarea (vacío si no necesita)
celery_app.conf.beat_schedule = {
    "verificar-vencimientos-periodico": {
        "task": "src.workers.tasks.verificar_vencimientos",
        "schedule": VERIFICATION_INTERVAL_SECONDS,
    },
    "limpiar-notificaciones-diario": {
        "task": "src.workers.tasks.limpiar_notificaciones_antiguas",
        "schedule": crontab(hour=3, minute=0),
    },
}
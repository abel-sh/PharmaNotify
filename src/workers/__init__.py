"""
Paquete de workers del sistema PharmaNotify.

Contiene la configuración de Celery (celery_app.py) y las tareas
distribuidas que se ejecutan en segundo plano (tasks.py):
  - notificar_evento: persiste y publica notificaciones de eventos CRUD.
  - verificar_vencimientos: detecta medicamentos próximos a vencer.
  - limpiar_notificaciones_antiguas: elimina notificaciones leídas antiguas.

La instancia `celery_app` se re-exporta aquí para que Celery la descubra
automáticamente al usar `-A src.workers` desde la línea de comandos.
"""

from src.workers.celery_app import celery_app

__all__ = ["celery_app"]
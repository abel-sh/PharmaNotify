"""
Paquete de workers del sistema PharmaNotify.

Contiene la configuración de Celery (celery_app.py) y las tareas
distribuidas que se ejecutan en segundo plano (tasks.py):
  - tarea_de_prueba: verifica que el sistema Celery está operativo.
  - verificar_vencimientos: detecta medicamentos próximos a vencer (Issue #9).
  - eliminar_vencidos: desactiva medicamentos expirados automáticamente (Issue #10).
  - notificar_evento: persiste y publica notificaciones de eventos CRUD (Issue #8).

La instancia `celery_app` se re-exporta aquí para que Celery la descubra
automáticamente al usar `-A src.workers` desde la línea de comandos.
"""

from src.workers.celery_app import celery_app

__all__ = ["celery_app"]
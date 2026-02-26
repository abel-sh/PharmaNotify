"""
Paquete raíz de PharmaNotify.

Estructura interna:
  shared/          → configuración, logger y protocolo compartidos
  infrastructure/  → conexiones a servicios externos y repositorios de datos
  server/          → servidor AsyncIO (TCP + IPC + Redis pub/sub)
  client/          → cliente CLI de farmacia
  monitor/         → monitor administrativo (IPC)
  workers/         → tareas distribuidas de Celery
  utils/           → utilidades compartidas (input, validación, excepciones)
"""
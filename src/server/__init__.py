"""
Paquete del servidor de PharmaNotify.

Módulo principal:
  server.py → orquesta las tres corrutinas concurrentes del servidor
              (TCP, IPC, Redis pub/sub) y despacha operaciones a los
              repositorios de la capa de infraestructura.
"""
# Configuración centralizada del logging para todos los componentes del sistema.
import logging
import sys


# =============================================================================
# Formato del log
# =============================================================================
# Cada línea de log va a verse así:
#   2025-07-15 14:32:01 [INFO] servidor: Cliente 'Farmacia del Centro' conectado
#
# Desglose del formato:
#   %(asctime)s   → Fecha y hora (2025-07-15 14:32:01)
#   %(levelname)s → Nivel del mensaje (INFO, WARNING, ERROR)
#   %(name)s      → Nombre del logger (servidor, cliente, monitor, worker)
#   %(message)s   → El mensaje en sí
FORMATO_LOG = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def obtener_logger(nombre: str, nivel: int = logging.INFO) -> logging.Logger:
    """
    Crea y devuelve un logger configurado con el formato estándar del sistema.

    :param nombre: Identificador del componente (ej: "servidor", "cliente", "worker").
                   Aparece en cada línea de log para saber de dónde viene el mensaje.
    :param nivel:  Nivel mínimo de mensajes a mostrar. Por defecto INFO.
                   Los niveles de menor a mayor severidad son:
                     DEBUG    → Detalles internos (solo para desarrollo)
                     INFO     → Operaciones normales (conexiones, CRUD exitosos)
                     WARNING  → Situaciones de atención (medicamentos por vencer,
                                acciones destructivas, desconexiones inesperadas)
                     ERROR    → Fallos que impiden completar una operación
                                (BD caída, Redis no disponible, mensaje malformado)
    :return: Logger listo para usar
    """
    # getLogger con un nombre específico devuelve siempre el MISMO logger
    # si se llama dos veces con el mismo nombre. Esto evita duplicación:
    # no importa cuántas veces importes y llames obtener_logger("servidor"),
    # siempre obtenés la misma instancia.
    logger = logging.getLogger(nombre)
    logger.setLevel(nivel)

    # Solo agregamos el handler si el logger no tiene uno todavía.
    # Sin esta verificación, cada vez que alguien llame obtener_logger()
    # se agregaría un handler nuevo, y los mensajes se imprimirían duplicados.
    if not logger.handlers:
        # StreamHandler(sys.stdout) envía los logs a la terminal.
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(nivel)

        # El Formatter le dice al handler cómo formatear cada mensaje.
        formateador = logging.Formatter(FORMATO_LOG, datefmt=FORMATO_FECHA)
        handler.setFormatter(formateador)

        logger.addHandler(handler)

    return logger
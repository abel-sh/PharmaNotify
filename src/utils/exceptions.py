"""
Excepciones personalizadas del sistema PharmaNotify.
Separadas en su propio módulo para que cualquier componente
(cliente, monitor) pueda importarlas sin depender del otro.
"""


class OperacionCancelada(Exception):
    """
    Se lanza cuando el usuario escribe 'cancelar' durante una operación.
    Permite abortar cualquier secuencia de inputs y volver al menú principal
    sin importar en qué paso de la operación se encuentre.
    """
    pass
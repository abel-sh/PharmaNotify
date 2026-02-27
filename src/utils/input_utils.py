"""
Utilidades para recolección y validación de input del usuario.

Separadas del cliente para que el monitor pueda reutilizarlas
sin depender del paquete client. Ambos componentes tienen menús interactivos
con las mismas necesidades de validación.
"""

import asyncio
from datetime import datetime
from src.shared.exceptions import OperacionCancelada


async def input_async(prompt: str = "") -> str:
    """
    Versión no bloqueante de input().
    Corre input() en un hilo separado para no congelar el event loop,
    permitiendo que escuchar_servidor() siga corriendo en paralelo.
    Si el usuario escribe 'cancelar', lanza OperacionCancelada para
    abortar la operación actual y volver al menú.
    """
    loop = asyncio.get_event_loop()
    valor = await loop.run_in_executor(None, input, prompt)
    if valor.strip().lower() == "cancelar":
        print("  Operación cancelada.")
        raise OperacionCancelada()
    return valor


async def input_requerido(prompt: str) -> str:
    """
    Repite la pregunta hasta que el usuario ingrese al menos un carácter.
    Evita enviar campos vacíos al servidor, que generarían registros inválidos.
    """
    while True:
        valor = await input_async(prompt)
        if valor.strip():
            return valor.strip()
        print("  ✘ Este campo es obligatorio. Escribí 'cancelar' para volver al menú.")


async def input_entero_positivo(prompt: str) -> int:
    """
    Repite la pregunta hasta recibir un número entero mayor a cero.
    Usada para campos como umbral_dias donde un texto o un cero
    no tienen sentido semántico en el sistema.
    """
    while True:
        valor = await input_async(prompt)
        try:
            numero = int(valor.strip())
            if numero > 0:
                return numero
            print("  ✘ El valor debe ser mayor a cero. Escribí 'cancelar' para volver al menú.")
        except ValueError:
            print("  ✘ Ingresá un número entero válido. Escribí 'cancelar' para volver al menú.")


def validar_fecha(fecha: str) -> bool:
    """
    Verifica que la fecha tenga el formato YYYY-MM-DD que espera la BD.
    Se valida en el cliente antes de enviar para evitar errores en el servidor.
    """
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except ValueError:
        return False
"""
Monitor administrativo de PharmaNotify.

Proceso CLI independiente que se comunica con el servidor a través
de un Unix Domain Socket (IPC). Permite gestionar farmacias (alta,
baja, renombrado, activación), consultar estadísticas del sistema,
y forzar la ejecución de tareas de Celery.

A diferencia del cliente, el monitor usa un patrón request-response
puro: abre una conexión por cada comando, envía, recibe, y cierra.
No mantiene una conexión persistente con el servidor.
"""

import asyncio
import argparse

from src.shared import (
    MONITOR_SOCKET_PATH,
    enviar_mensaje, recibir_mensaje,
    obtener_logger
)

from src.shared.exceptions import OperacionCancelada
from src.utils.input_utils import input_async, input_requerido
from src.monitor.ui import mostrar_menu, mostrar_respuesta

logger = obtener_logger("monitor")


async def enviar_comando(socket_path: str, comando: dict) -> dict:
    """
    Abre una conexión al Unix Domain Socket del servidor, manda un comando,
    espera la respuesta, y cierra. Una conexión por comando.

    Este patrón es intencional: el monitor es una herramienta de administración
    ocasional, no un cliente permanente. Abrir y cerrar por comando mantiene
    el servidor sin estado extra que gestionar.
    """
    try:
        reader, writer = await asyncio.open_unix_connection(socket_path)
        await enviar_mensaje(writer, comando)
        respuesta = await recibir_mensaje(reader)
        writer.close()
        await writer.wait_closed()
        return respuesta or {"ok": False, "mensaje": "El servidor no respondió."}

    except FileNotFoundError:
        return {
            "ok": False,
            "mensaje": f"No se encontró el socket en '{socket_path}'. ¿Está corriendo el servidor?"
        }
    except ConnectionRefusedError:
        return {
            "ok": False,
            "mensaje": "El servidor rechazó la conexión IPC."
        }
    except Exception as e:
        return {"ok": False, "mensaje": f"Error de conexión: {e}"}


async def loop_monitor(socket_path: str) -> None:
    """
    Loop principal del monitor administrativo.
    Muestra el menú, captura la opción del usuario, y envía
    el comando correspondiente al servidor por IPC.
    Cada iteración del loop es un comando completo:
    mostrar menú → leer opción → enviar → mostrar respuesta.
    """
    while True:
        mostrar_menu()

        try:
            opcion = await input_async()
            opcion = opcion.strip()

            if opcion == "1":
                print("\n-- Registrar farmacia --")
                nombre = await input_requerido("  Nombre de la farmacia: ")
                respuesta = await enviar_comando(socket_path, {
                    "accion": "crear_farmacia",
                    "nombre": nombre
                })
                mostrar_respuesta(respuesta)

            elif opcion == "2":
                respuesta = await enviar_comando(socket_path, {
                    "accion": "listar_farmacias"
                })
                mostrar_respuesta(respuesta)

            elif opcion == "3":
                print("\n-- Renombrar farmacia --")
                nombre_actual = await input_requerido("  Nombre actual: ")
                nombre_nuevo  = await input_requerido("  Nombre nuevo:  ")
                confirmar = await input_async(
                    f"  ⚠ ¿Confirma renombrar '{nombre_actual}' → '{nombre_nuevo}'? [s/N]: "
                )
                if confirmar.strip().lower() != "s":
                    print("  Operación cancelada.")
                    continue
                respuesta = await enviar_comando(socket_path, {
                    "accion": "renombrar_farmacia",
                    "nombre_actual": nombre_actual,
                    "nombre_nuevo": nombre_nuevo
                })
                mostrar_respuesta(respuesta)

            elif opcion == "4":
                print("\n-- Desactivar farmacia --")
                nombre = await input_requerido("  Nombre de la farmacia a desactivar: ")
                confirmar = await input_async(
                    f"  ⚠ ¿Confirma desactivar '{nombre}'? "
                    f"Si está conectada será desconectada. [s/N]: "
                )
                if confirmar.strip().lower() != "s":
                    print("  Operación cancelada.")
                    continue
                respuesta = await enviar_comando(socket_path, {
                    "accion": "desactivar_farmacia",
                    "nombre": nombre
                })
                mostrar_respuesta(respuesta)

            elif opcion == "5":
                print("\n-- Activar farmacia --")
                nombre = await input_requerido("  Nombre de la farmacia a activar: ")
                confirmar = await input_async(
                    f"  ¿Confirma reactivar '{nombre}'? [s/N]: "
                )
                if confirmar.strip().lower() != "s":
                    print("  Operación cancelada.")
                    continue
                respuesta = await enviar_comando(socket_path, {
                    "accion": "activar_farmacia",
                    "nombre": nombre
                })
                mostrar_respuesta(respuesta)

            elif opcion == "6":
                respuesta = await enviar_comando(socket_path, {"accion": "status"})
                mostrar_respuesta(respuesta)

            elif opcion == "7":
                respuesta = await enviar_comando(socket_path, {"accion": "estadisticas"})
                mostrar_respuesta(respuesta)

            elif opcion == "8":
                confirmar = await input_async(
                    "  ⚠ ¿Forzar verificación de vencimientos ahora? [s/N]: "
                )
                if confirmar.strip().lower() == "s":
                    respuesta = await enviar_comando(socket_path, {
                        "accion": "run_tarea",
                        "tarea": "verificar_vencimientos"
                    })
                    mostrar_respuesta(respuesta)
                else:
                    print("  Operación cancelada.")

            elif opcion == "9":
                confirmar = await input_async(
                    "  ⚠ ¿Forzar limpieza de notificaciones antiguas ahora? [s/N]: "
                )
                if confirmar.strip().lower() == "s":
                    respuesta = await enviar_comando(socket_path, {
                        "accion": "run_tarea",
                        "tarea": "limpiar_notificaciones"
                    })
                    mostrar_respuesta(respuesta)
                else:
                    print("  Operación cancelada.")

            elif opcion == "10":
                print("Cerrando monitor. Hasta luego.")
                break

            else:
                print("  Opción no válida. Ingresá un número del 1 al 10.")

        except OperacionCancelada:
            pass


def parsear_argumentos():
    """
    Procesa los argumentos de línea de comandos del monitor:
    --socket con la ruta del Unix Domain Socket del servidor.
    """
    parser = argparse.ArgumentParser(
        description="PharmaNotify — Monitor de administración del sistema"
    )
    parser.add_argument(
        "--socket",
        default=MONITOR_SOCKET_PATH,
        help=f"Ruta del Unix Domain Socket del servidor (default: {MONITOR_SOCKET_PATH})"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parsear_argumentos()
    asyncio.run(loop_monitor(args.socket))
import asyncio
import argparse
import logging

from src.shared import (
    SERVER_HOST, SERVER_PORT,
    enviar_mensaje, recibir_mensaje
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def mostrar_resumen(resumen: dict) -> None:
    """
    Muestra en pantalla el resumen de estado que envía el servidor
    justo después de que la farmacia se conecta.
    """
    print("\n+--------------------------------------+")
    print("|         RESUMEN DE ESTADO             |")
    print("+---------------------------------------+")
    print(f"  Medicamentos activos:      {resumen.get('medicamentos_activos', 0)}")
    print(f"  Notificaciones no leídas:  {resumen.get('notificaciones_no_leidas', 0)}")

    vencidos = resumen.get("vencidos_mientras_ausente", [])
    if vencidos:
        print(f"\n  ⚠ Medicamentos vencidos mientras estabas desconectado:")
        for v in vencidos:
            print(f"    - {v['nombre']} (venció: {v['fecha_vencimiento']})")
    print("+--------------------------------------+\n")


def mostrar_menu() -> None:
    print("\n+--------------------------------------+")
    print("|           PHARMA NOTIFY              |")
    print("+--------------------------------------+")
    print("|  1. Crear medicamento                |")
    print("|  2. Listar medicamentos              |")
    print("|  3. Buscar medicamento               |")
    print("|  4. Actualizar medicamento           |")
    print("|  5. Eliminar medicamento             |")
    print("|  6. Ver notificaciones               |")
    print("|  7. Configurar umbral de alertas     |")
    print("|  8. Salir                            |")
    print("+--------------------------------------+")
    print("Opción: ", end="", flush=True)


async def escuchar_servidor(reader: asyncio.StreamReader) -> None:
    """
    Corrutina que corre en paralelo al loop del menú.
    Su única responsabilidad es esperar mensajes del servidor
    (notificaciones, respuestas a comandos) y mostrarlos en pantalla.
    
    Cuando el servidor cierra la conexión, recibir_mensaje lanza
    IncompleteReadError y esta corrutina termina limpiamente.
    """
    try:
        while True:
            mensaje = await recibir_mensaje(reader)
            if mensaje is None:
                break

            tipo = mensaje.get("tipo", "")

            # Los distintos tipos de mensaje del servidor
            # se van a ir expandiendo a medida que avancen los issues.
            if tipo == "notificacion":
                print(f"\n🔔 NOTIFICACIÓN: {mensaje.get('mensaje', '')}")
                print("Opción: ", end="", flush=True)  # re-mostramos el prompt
            elif tipo == "respuesta":
                print(f"\n✔ {mensaje.get('mensaje', '')}")
                print("Opción: ", end="", flush=True)
            elif tipo == "error":
                print(f"\n✘ Error: {mensaje.get('mensaje', '')}")
                print("Opción: ", end="", flush=True)
            else:
                # Cualquier mensaje que no reconozcamos lo logueamos
                # para facilitar el debugging durante el desarrollo.
                logger.info(f"Mensaje del servidor: {mensaje}")

    except asyncio.IncompleteReadError:
        print("\nEl servidor cerró la conexión.")
    except Exception as e:
        logger.error(f"Error en la escucha del servidor: {e}")


async def input_async(prompt: str = "") -> str:
    """
    Versión no bloqueante de input().
    
    input() es bloqueante: cuando Python la llama, congela el event loop
    hasta que el usuario presiona Enter. Eso impediría que escuchar_servidor()
    pudiera correr al mismo tiempo.
    
    run_in_executor() corre input() en un hilo separado del sistema operativo,
    fuera del event loop, y le devuelve el control a AsyncIO mientras espera.
    Cuando el usuario presiona Enter, el resultado vuelve al event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


async def loop_menu(writer: asyncio.StreamWriter, nombre_farmacia: str) -> None:
    """
    Corrutina que gestiona el menú interactivo.
    Corre en paralelo con escuchar_servidor().
    
    Por ahora cada opción construye un diccionario y lo envía al servidor.
    El servidor todavía no los procesa (eso llega en el Issue 6),
    pero el flujo de comunicación ya está completo.
    """
    while True:
        mostrar_menu()
        opcion = await input_async()
        opcion = opcion.strip()

        if opcion == "1":
            print("\n-- Crear medicamento --")
            codigo    = await input_async("Código: ")
            nombre    = await input_async("Nombre: ")
            vence     = await input_async("Fecha de vencimiento (YYYY-MM-DD): ")
            await enviar_mensaje(writer, {
                "accion": "crear_medicamento",
                "codigo": codigo.strip(),
                "nombre": nombre.strip(),
                "fecha_vencimiento": vence.strip()
            })

        elif opcion == "2":
            await enviar_mensaje(writer, {"accion": "listar_medicamentos"})

        elif opcion == "3":
            codigo = await input_async("Código del medicamento: ")
            await enviar_mensaje(writer, {
                "accion": "buscar_medicamento",
                "codigo": codigo.strip()
            })

        elif opcion == "4":
            codigo = await input_async("Código del medicamento a actualizar: ")
            confirmar = await input_async(
                f"⚠ ¿Está seguro que desea actualizar '{codigo.strip()}'? [s/N]: "
            )
            if confirmar.strip().lower() == "s":
                nombre = await input_async("Nuevo nombre (Enter para no cambiar): ")
                vence  = await input_async("Nueva fecha de vencimiento (Enter para no cambiar): ")
                await enviar_mensaje(writer, {
                    "accion": "actualizar_medicamento",
                    "codigo": codigo.strip(),
                    "nombre": nombre.strip() or None,
                    "fecha_vencimiento": vence.strip() or None
                })
            else:
                print("Operación cancelada.")

        elif opcion == "5":
            codigo = await input_async("Código del medicamento a eliminar: ")
            confirmar = await input_async(
                f"⚠ ¿Está seguro que desea eliminar '{codigo.strip()}'? [s/N]: "
            )
            if confirmar.strip().lower() == "s":
                await enviar_mensaje(writer, {
                    "accion": "eliminar_medicamento",
                    "codigo": codigo.strip()
                })
            else:
                print("Operación cancelada.")

        elif opcion == "6":
            await enviar_mensaje(writer, {"accion": "ver_notificaciones"})

        elif opcion == "7":
            dias = await input_async("Nuevo umbral de alertas (días): ")
            await enviar_mensaje(writer, {
                "accion": "configurar_umbral",
                "umbral_dias": dias.strip()
            })

        elif opcion == "8":
            print("Cerrando conexión. Hasta luego.")
            break

        else:
            print("Opción no válida. Ingresá un número del 1 al 8.")


async def iniciar_cliente(host: str, puerto: int, nombre_farmacia: str) -> None:
    """
    Punto de entrada del cliente. Establece la conexión TCP,
    realiza el handshake inicial con el servidor, y luego
    lanza las dos corrutinas concurrentes: menú y escucha.
    """
    print(f"Conectando a {host}:{puerto} como '{nombre_farmacia}'...")

    try:
        reader, writer = await asyncio.open_connection(host, puerto)
    except ConnectionRefusedError:
        print("No se pudo conectar al servidor. ¿Está corriendo?")
        return

    # ── Handshake: enviamos el nombre de farmacia ─────────────────────────
    nombre_normalizado = nombre_farmacia.strip()
    await enviar_mensaje(writer, {"nombre_farmacia": nombre_normalizado})

    # ── Esperamos la respuesta del servidor ───────────────────────────────
    respuesta = await recibir_mensaje(reader)
    tipo = respuesta.get("tipo", "")

    if tipo == "rechazo":
        print(f"\n✘ Conexión rechazada: {respuesta.get('mensaje', '')}")
        writer.close()
        return

    if tipo == "resumen_estado":
        mostrar_resumen(respuesta)

    # ── Lanzamos las dos corrutinas concurrentes ──────────────────────────
    # asyncio.gather() las corre "a la vez" dentro del mismo event loop.
    # Si cualquiera de las dos termina (por error o por opción 8),
    # la otra se cancela automáticamente gracias al return_when.
    tarea_menu    = asyncio.create_task(loop_menu(writer, nombre_normalizado))
    tarea_escucha = asyncio.create_task(escuchar_servidor(reader))

    done, pending = await asyncio.wait(
        [tarea_menu, tarea_escucha],
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cancelamos la tarea que quedó pendiente
    for tarea in pending:
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass

    writer.close()
    await writer.wait_closed()


def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="PharmaNotify — Cliente CLI de farmacia"
    )
    parser.add_argument(
        "--host",
        default=SERVER_HOST,
        help=f"Host del servidor (default: {SERVER_HOST})"
    )
    parser.add_argument(
        "--puerto",
        type=int,
        default=SERVER_PORT,
        help=f"Puerto del servidor (default: {SERVER_PORT})"
    )
    parser.add_argument(
        "--farmacia",
        required=True,
        help="Nombre de la farmacia con la que conectarse"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parsear_argumentos()
    asyncio.run(iniciar_cliente(args.host, args.puerto, args.farmacia))
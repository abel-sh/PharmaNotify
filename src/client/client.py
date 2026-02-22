import asyncio
import argparse

from src.shared import (
    SERVER_HOST, SERVER_PORT,
    enviar_mensaje, recibir_mensaje,
    obtener_logger
)

from src.utils.exceptions import OperacionCancelada
from src.utils.input_utils import input_async, input_requerido, input_entero_positivo, validar_fecha
from src.client.ui import mostrar_menu, mostrar_resumen

logger = obtener_logger("cliente")


async def escuchar_servidor(reader: asyncio.StreamReader, cola_respuestas: asyncio.Queue, esperando_respuesta: asyncio.Event) -> None:
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

            # Si loop_menu está esperando una respuesta puntual (verificación previa),
            # depositamos el mensaje en la queue para que lo consuma directamente.
            # Después de depositar, continuamos al siguiente ciclo sin mostrar nada.
            if esperando_respuesta.is_set():
                await cola_respuestas.put(mensaje)
                continue

            # Comportamiento normal: mostramos el mensaje en pantalla
            tipo = mensaje.get("tipo", "")

            if tipo == "notificacion":
                print(f"\n🔔 NOTIFICACIÓN: {mensaje.get('mensaje', '')}")
                print("Opción: ", end="", flush=True)

            elif tipo == "respuesta":
                if "medicamentos" in mensaje:
                    meds = mensaje["medicamentos"]
                    if not meds:
                        print("\n  No hay medicamentos registrados.")
                    else:
                        print(f"\n  {'CÓDIGO':<15} {'NOMBRE':<30} {'VENCE':<15}")
                        print("  " + "─" * 60)
                        for m in meds:
                            print(f"  {m['codigo']:<15} {m['nombre']:<30} {m['fecha_vencimiento']:<15}")
                elif "medicamento" in mensaje:
                    m = mensaje["medicamento"]
                    print(f"\n  Código:      {m['codigo']}")
                    print(f"  Nombre:      {m['nombre']}")
                    print(f"  Vencimiento: {m['fecha_vencimiento']}")
                elif "notificaciones" in mensaje:
                    notifs = mensaje["notificaciones"]
                    if not notifs:
                        print("\n  No hay notificaciones para mostrar.")
                    else:
                        print(f"\n  {'#':<5} {'TIPO':<15} {'MENSAJE':<45} {'LEÍDA':<6} {'FECHA'}")
                        print("  " + "─" * 80)
                        for n in notifs:
                            leida = "Sí" if n["leida"] else "No"
                            # Truncamos el mensaje a 45 caracteres para que la tabla
                            # no se rompa visualmente si el mensaje es muy largo.
                            mensaje_corto = n["mensaje"][:42] + "..." if len(n["mensaje"]) > 45 else n["mensaje"]
                            print(
                                f"  {n['id']:<5} {n['tipo']:<15} "
                                f"{mensaje_corto:<45} {leida:<6} {n['creado_en']}"
                            )
                else:
                    simbolo = "✔" if mensaje.get("ok") else "✘"
                    print(f"\n  {simbolo} {mensaje.get('mensaje', '')}")
                print("Opción: ", end="", flush=True)

            elif tipo == "error":
                print(f"\n  ✘ Error: {mensaje.get('mensaje', '')}")
                print("Opción: ", end="", flush=True)

            else:
                logger.info(f"Mensaje del servidor: {mensaje}")

    except asyncio.IncompleteReadError:
        print("\nEl servidor cerró la conexión.")
    except Exception as e:
        logger.error(f"Error en la escucha del servidor: {e}")


async def loop_menu(writer: asyncio.StreamWriter, nombre_farmacia: str, cola_respuestas: asyncio.Queue, esperando_respuesta: asyncio.Event) -> None:
    """
    Corrutina que gestiona el menú interactivo.
    Corre en paralelo con escuchar_servidor().

    Cada opción construye un diccionario con el campo "accion" y los datos
    necesarios, y lo envía al servidor. El servidor lo despacha a manejar_crud()
    según ese campo, ejecuta la operación en la BD, y responde. Esa respuesta
    la procesa escuchar_servidor() en la otra corrutina.
    """
    while True:
        mostrar_menu()

        try:
            opcion = await input_async()
            opcion = opcion.strip()

            if opcion == "1":
                print("\n-- Crear medicamento --")
                # Código y nombre son obligatorios: usamos input_requerido
                # para garantizar que nunca lleguen vacíos al servidor.
                codigo = await input_requerido("  Código: ")
                nombre = await input_requerido("  Nombre: ")

                # La fecha tiene su propia validación de formato.
                # El loop repite la pregunta hasta recibir una fecha válida.
                while True:
                    vence = await input_async("  Fecha de vencimiento (YYYY-MM-DD, ej: 2026-08-15): ")
                    if validar_fecha(vence.strip()):
                        break
                    print("  ✘ Formato de fecha inválido. Usá el formato YYYY-MM-DD (ej: 2026-08-15).")

                await enviar_mensaje(writer, {
                    "accion": "crear_medicamento",
                    "codigo": codigo,
                    "nombre": nombre,
                    "fecha_vencimiento": vence.strip()
                })

            elif opcion == "2":
                await enviar_mensaje(writer, {"accion": "listar_medicamentos"})

            elif opcion == "3":
                # El código es obligatorio: buscar con un código vacío no tiene sentido
                codigo = await input_requerido("  Código del medicamento: ")
                await enviar_mensaje(writer, {
                    "accion": "buscar_medicamento",
                    "codigo": codigo
                })

            elif opcion == "4":
                # El código es obligatorio antes de consultar al servidor
                codigo = await input_requerido("  Código del medicamento a actualizar: ")

                try:
                    # Activamos el event ANTES de enviar la consulta al servidor.
                    # Esto le indica a escuchar_servidor que el próximo mensaje
                    # que llegue debe ir a la queue, no a la pantalla.
                    esperando_respuesta.set()
                    await enviar_mensaje(writer, {
                        "accion": "buscar_medicamento",
                        "codigo": codigo
                    })

                    # Esperamos asincrónicamente hasta que escuchar_servidor
                    # deposite la respuesta en la queue.
                    respuesta = await cola_respuestas.get()

                finally:
                    # El finally garantiza que el event siempre se desactiva,
                    # incluso si el usuario cancela mientras esperamos la respuesta.
                    # Sin esto, el event podría quedar activo y contaminar
                    # la siguiente operación con una respuesta "vieja".
                    esperando_respuesta.clear()

                if not respuesta.get("ok"):
                    print(f"  ✘ {respuesta.get('mensaje', 'Medicamento no encontrado.')}")
                    continue

                print(f"  ✔ Medicamento encontrado. Ingresá los nuevos valores.")
                confirmar = await input_async(
                    f"  ⚠ ¿Está seguro que desea actualizar '{codigo}' "
                    f"en {nombre_farmacia}? [s/N]: "
                )
                if confirmar.strip().lower() == "s":
                    nombre = await input_async("  Nuevo nombre (Enter para no cambiar): ")

                    vence = ""
                    while True:
                        vence = await input_async(
                            "  Nueva fecha de vencimiento (YYYY-MM-DD, ej: 2026-08-15, Enter para no cambiar): "
                        )
                        # Campo vacío es válido: significa "no cambiar este campo"
                        if vence.strip() == "" or validar_fecha(vence.strip()):
                            break
                        print("  ✘ Formato inválido. Usá YYYY-MM-DD (ej: 2026-08-15).")

                    await enviar_mensaje(writer, {
                        "accion": "actualizar_medicamento",
                        "codigo": codigo,
                        "nombre": nombre.strip() or None,
                        "fecha_vencimiento": vence.strip() or None
                    })
                else:
                    print("  Operación cancelada.")

            elif opcion == "5":
                # El código es obligatorio: no tiene sentido intentar eliminar sin especificar cuál
                codigo = await input_requerido("  Código del medicamento a eliminar: ")
                confirmar = await input_async(
                    f"  ⚠ ¿Está seguro que desea eliminar '{codigo}' "
                    f"de {nombre_farmacia}? [s/N]: "
                )
                if confirmar.strip().lower() == "s":
                    await enviar_mensaje(writer, {
                        "accion": "eliminar_medicamento",
                        "codigo": codigo
                    })
                else:
                    print("  Operación cancelada.")

            elif opcion == "6":
                await enviar_mensaje(writer, {"accion": "ver_notificaciones"})

            elif opcion == "7":
                # Usamos input_entero_positivo porque un umbral de 0 o texto
                # no tienen sentido como días de anticipación para alertas
                dias = await input_entero_positivo("  Nuevo umbral de alertas (días): ")
                await enviar_mensaje(writer, {
                    "accion": "configurar_umbral",
                    "umbral_dias": dias  # ya es int, no necesita .strip()
                })

            elif opcion == "8":
                print("Cerrando conexión. Hasta luego.")
                break

            else:
                print("  Opción no válida. Ingresá un número del 1 al 8.")

        except OperacionCancelada:
            # La excepción ya mostró "Operación cancelada." en input_async.
            # Simplemente dejamos que el while True vuelva a mostrar el menú.
            pass


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

    # Handshake: enviamos el nombre de farmacia al servidor
    nombre_normalizado = nombre_farmacia.strip()
    await enviar_mensaje(writer, {"nombre_farmacia": nombre_normalizado})

    # Esperamos la respuesta del servidor: aceptación o rechazo
    respuesta = await recibir_mensaje(reader)
    tipo = respuesta.get("tipo", "")

    if tipo == "rechazo":
        print(f"\n  ✘ Conexión rechazada: {respuesta.get('mensaje', '')}")
        writer.close()
        return

    if tipo == "resumen_estado":
        mostrar_resumen(respuesta)

    # La queue transporta respuestas desde escuchar_servidor hacia loop_menu
    # cuando este último necesita hacer una consulta puntual al servidor.
    # El event actúa como señal: loop_menu lo activa cuando está esperando,
    # escuchar_servidor lo consulta para saber a dónde rutear el mensaje.
    cola_respuestas     = asyncio.Queue()
    esperando_respuesta = asyncio.Event()

    tarea_menu    = asyncio.create_task(loop_menu(writer, nombre_normalizado, cola_respuestas, esperando_respuesta))
    tarea_escucha = asyncio.create_task(escuchar_servidor(reader, cola_respuestas, esperando_respuesta))

    # FIRST_COMPLETED: cuando cualquiera de las dos tareas termine
    # (el usuario eligió salir, o el servidor cerró la conexión),
    # cancelamos la otra y cerramos limpiamente.
    _, pending = await asyncio.wait(
        [tarea_menu, tarea_escucha],
        return_when=asyncio.FIRST_COMPLETED
    )

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
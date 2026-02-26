"""
Servidor principal de PharmaNotify.

Orquesta tres corrutinas concurrentes dentro del mismo event loop:
  1. Servidor TCP — acepta conexiones de farmacias y despacha
     operaciones CRUD delegando a los repositorios.
  2. Servidor IPC (Unix Domain Socket) — acepta comandos del
     monitor administrativo.
  3. Suscriptor Redis pub/sub — recibe notificaciones generadas
     por los workers de Celery y las reenvía a los clientes conectados.

El servidor actúa como coordinador: no contiene lógica de negocio
ni acceso directo a la BD. Toda operación de datos la delega a la
capa de repositorios en infrastructure/repositories/.
"""

import asyncio
import argparse
import json
import os

from src.shared import (
    SERVER_HOST, SERVER_PORT,
    REDIS_NOTIFICATIONS_CHANNEL,
    MONITOR_SOCKET_PATH,
    enviar_mensaje, recibir_mensaje,
    obtener_logger
)

from src.infrastructure import (
    get_async_connection,
    get_async_redis_client,
    crear_medicamento,
    listar_medicamentos,
    buscar_medicamento,
    actualizar_medicamento,
    eliminar_medicamento,
    ver_notificaciones,
    buscar_farmacia_por_nombre,      
    configurar_umbral,
    obtener_resumen_farmacia,
    # Nuevas para el monitor
    crear_farmacia,
    listar_farmacias,
    renombrar_farmacia,
    activar_farmacia,
    desactivar_farmacia,
    obtener_estadisticas,
)

from src.workers.tasks import notificar_evento

logger = obtener_logger("servidor")

# Registro global de clientes actualmente conectados.
# Para buscar por nombre al conectar
clientes_conectados: dict[str, asyncio.StreamWriter] = {}

# Se mantienen sincronizados: cuando se agrega/elimina en uno, se hace en el otro.
# (para buscar por id al notificar)
clientes_por_id: dict[int, asyncio.StreamWriter] = {}


async def escuchar_notificaciones_redis():
    """
    Corrutina que se suscribe al canal Redis de notificaciones y reenvía
    cada mensaje al cliente conectado correspondiente.

    Corre permanentemente dentro del mismo event loop que el servidor TCP,
    conviviendo con todas las conexiones de clientes sin bloquearlas.
    Es la implementación del patrón Observer en el servidor:
    Redis es el sujeto observable, y esta corrutina es el observador.
    """
    # Creamos un cliente Redis asíncrono para no bloquear el event loop.
    cliente = get_async_redis_client()
    pubsub  = cliente.pubsub()

    # Nos suscribimos al canal. A partir de este momento, Redis nos enviará
    # todos los mensajes que se publiquen en REDIS_NOTIFICATIONS_CHANNEL.
    await pubsub.subscribe(REDIS_NOTIFICATIONS_CHANNEL)
    logger.info(f"Suscrito al canal Redis: {REDIS_NOTIFICATIONS_CHANNEL}")

    try:
        # listen() es un generador asíncrono: cada vez que llega un mensaje
        # al canal, yield lo entrega acá y el event loop puede atender
        # otras tareas mientras esperamos el próximo mensaje.
        async for mensaje_raw in pubsub.listen():

            # El primer mensaje que llega después de subscribe() es una
            # confirmación de suscripción con tipo "subscribe", no un mensaje real.
            # Lo ignoramos.
            if mensaje_raw["type"] != "message":
                continue

            try:
                # El dato viene como bytes, lo decodificamos y parseamos.
                payload = json.loads(mensaje_raw["data"].decode("utf-8"))
                farmacia_id = payload.get("farmacia_id")
                mensaje_texto = payload.get("mensaje", "")

                # NOTA: para poder buscar por farmacia_id necesitamos cambiar
                # clientes_conectados para que guarde también el id.
                # Lo ajustamos en manejar_cliente más abajo.
                if farmacia_id in clientes_por_id:
                    writer_destino = clientes_por_id[farmacia_id]
                    await enviar_mensaje(writer_destino, {
                        "tipo": "notificacion",
                        "mensaje": mensaje_texto
                    })
                    logger.info(
                        f"Notificación reenviada a farmacia_id={farmacia_id}"
                    )
                else:
                    logger.info(
                        f"Notificación para farmacia_id={farmacia_id} "
                        f"generada pero la farmacia no está conectada. "
                        f"Quedó persistida en la BD."
                    )

            except Exception as e:
                logger.error(f"Error procesando notificación de Redis: {e}")

    except asyncio.CancelledError:
        # Se lanza cuando el servidor se está cerrando.
        # Cancelamos la suscripción limpiamente.
        await pubsub.unsubscribe(REDIS_NOTIFICATIONS_CHANNEL)
        await cliente.aclose()


async def manejar_crud(conn, writer: asyncio.StreamWriter, farmacia_id: int, mensaje: dict) -> None:
    """
    Despachador central de operaciones CRUD.
    Ahora, además de ejecutar la operación y responder al cliente,
    despacha una tarea notificar_evento a Celery por cada operación exitosa.
    """
    accion = mensaje.get("accion", "")

    if accion == "crear_medicamento":
        resultado = await crear_medicamento(
            conn, farmacia_id,
            mensaje.get("codigo", ""),
            mensaje.get("nombre", ""),
            mensaje.get("fecha_vencimiento", "")
        )
        logger.info(f"[farmacia_id={farmacia_id}] crear_medicamento '{mensaje.get('codigo')}' → {resultado['ok']}")
        await enviar_mensaje(writer, {"tipo": "respuesta", **resultado})

        # Despachamos la notificación solo si la operación fue exitosa.
        # .delay() es no bloqueante: encola la tarea en Redis y continúa
        # inmediatamente sin esperar a que el worker la procese.
        if resultado["ok"]:
            notificar_evento.delay(
                farmacia_id=farmacia_id,
                tipo="creacion",
                mensaje=f"Medicamento '{mensaje.get('nombre')}' (código: {mensaje.get('codigo')}) agregado al inventario."
            )

    elif accion == "listar_medicamentos":
        resultado = await listar_medicamentos(conn, farmacia_id)
        logger.info(f"[farmacia_id={farmacia_id}] listar_medicamentos → {len(resultado.get('medicamentos', []))} registros")
        await enviar_mensaje(writer, {"tipo": "respuesta", **resultado})
        # Listar no genera notificación: es una consulta, no un evento de negocio.

    elif accion == "buscar_medicamento":
        resultado = await buscar_medicamento(conn, farmacia_id, mensaje.get("codigo", ""))
        logger.info(f"[farmacia_id={farmacia_id}] buscar_medicamento '{mensaje.get('codigo')}' → {resultado['ok']}")
        await enviar_mensaje(writer, {"tipo": "respuesta", **resultado})
        # Buscar tampoco genera notificación por el mismo motivo.

    elif accion == "actualizar_medicamento":
        resultado = await actualizar_medicamento(
            conn, farmacia_id,
            mensaje.get("codigo", ""),
            mensaje.get("nombre"),
            mensaje.get("fecha_vencimiento")
        )
        logger.info(f"[farmacia_id={farmacia_id}] actualizar_medicamento '{mensaje.get('codigo')}' → {resultado['ok']}")
        await enviar_mensaje(writer, {"tipo": "respuesta", **resultado})

        if resultado["ok"]:
            notificar_evento.delay(
                farmacia_id=farmacia_id,
                tipo="actualizacion",
                mensaje=f"Medicamento '{mensaje.get('codigo')}' actualizado en el inventario."
            )

    elif accion == "eliminar_medicamento":
        resultado = await eliminar_medicamento(conn, farmacia_id, mensaje.get("codigo", ""))
        logger.warning(f"[farmacia_id={farmacia_id}] eliminar_medicamento '{mensaje.get('codigo')}' → {resultado['ok']}")
        await enviar_mensaje(writer, {"tipo": "respuesta", **resultado})

        if resultado["ok"]:
            notificar_evento.delay(
                farmacia_id=farmacia_id,
                tipo="eliminacion",
                mensaje=f"Medicamento '{mensaje.get('codigo')}' eliminado del inventario."
            )

    elif accion == "ver_notificaciones":
        solo_no_leidas = mensaje.get("solo_no_leidas", False)
        resultado = await ver_notificaciones(conn, farmacia_id, solo_no_leidas)
        logger.info(
            f"[farmacia_id={farmacia_id}] ver_notificaciones "
            f"(solo_no_leidas={solo_no_leidas}) "
            f"→ {len(resultado.get('notificaciones', []))} registros"
        )
        await enviar_mensaje(writer, {"tipo": "respuesta", **resultado})

    elif accion == "configurar_umbral":
        resultado = await configurar_umbral(conn, farmacia_id, mensaje.get("umbral_dias", 7))
        logger.info(
            f"[farmacia_id={farmacia_id}] configurar_umbral → {resultado['ok']}"
        )
        await enviar_mensaje(writer, {"tipo": "respuesta", **resultado})

    elif accion == "resumen_estado":
        resultado = await obtener_resumen_farmacia(conn, farmacia_id)
        logger.info(
            f"[farmacia_id={farmacia_id}] resumen_estado solicitado manualmente"
        )
        # obtener_resumen_farmacia ya devuelve el tipo "resumen_estado",
        # que es exactamente el formato que espera mostrar_resumen() en el cliente.
        await enviar_mensaje(writer, resultado)

    else:
        logger.warning(f"[farmacia_id={farmacia_id}] Acción desconocida: '{accion}'")
        await enviar_mensaje(writer, {
            "tipo": "error",
            "mensaje": f"Acción '{accion}' no reconocida."
        })


async def manejar_cliente(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Corrutina que maneja el ciclo de vida completo de UN cliente conectado.
    AsyncIO la llama automáticamente cada vez que llega una nueva conexión TCP.
    Cada cliente tiene su propia instancia de esta corrutina corriendo de forma independiente.
    """
    # get_extra_info("peername") devuelve la IP y puerto del cliente que se conectó.
    # Sirve para identificarlo en los logs antes de saber su nombre de farmacia.
    direccion = writer.get_extra_info("peername")
    logger.info(f"Nueva conexión entrante desde {direccion}")

    conn = None             # conexión a la BD (la inicializamos más abajo)
    nombre_farmacia = None  # la necesitamos en el bloque finally para limpiar
    farmacia_id = None  

    try:
        # Recibir el primer mensaje del cliente
        # El primer mensaje que manda el cliente es simplemente su nombre de farmacia.
        mensaje_inicial = await recibir_mensaje(reader)
        nombre_farmacia_raw = mensaje_inicial.get("nombre_farmacia", "")

        # Normalizar el nombre 
        nombre_farmacia = nombre_farmacia_raw.strip()

        if not nombre_farmacia:
            await enviar_mensaje(writer, {
                "tipo": "error",
                "mensaje": "Nombre de farmacia vacío. Cerrando conexión."
            })
            return  # sale del try, va directo al finally

        # Buscar la farmacia en la BD
        conn = await get_async_connection()
        resultado = await buscar_farmacia_por_nombre(conn, nombre_farmacia)

        # Validar existencia
        if not resultado["encontrada"]:
            logger.warning(
                f"Intento de conexión con farmacia no registrada: "
                f"'{nombre_farmacia_raw}' desde {direccion}"
            )
            await enviar_mensaje(writer, {
                "tipo": "rechazo",
                "mensaje": f"La farmacia '{nombre_farmacia_raw}' no está registrada en el sistema."
            })
            return

        farmacia_id = resultado["farmacia_id"]
        farmacia_nombre = resultado["nombre"]
        farmacia_activa = resultado["activa"]

        if not farmacia_activa:
            logger.warning(
                f"Intento de conexión con farmacia desactivada: "
                f"'{farmacia_nombre}' desde {direccion}"
            )
            await enviar_mensaje(writer, {
                "tipo": "rechazo",
                "mensaje": f"La farmacia '{farmacia_nombre}' está desactivada."
            })
            return

        # Registrar y dar la bienvenida
        # Guardamos el writer en el diccionario global para poder enviarle
        # notificaciones a esta farmacia desde cualquier otro punto del servidor.
        clientes_conectados[nombre_farmacia.lower()] = writer
        clientes_por_id[farmacia_id] = writer
        logger.info(
            f"Farmacia '{farmacia_nombre}' conectada exitosamente. "
            f"Clientes activos: {len(clientes_conectados)}"
        )

        resumen = await obtener_resumen_farmacia(conn, farmacia_id)
        await enviar_mensaje(writer, resumen)

        # Loop de escucha
        while True:
            mensaje = await recibir_mensaje(reader)
            if mensaje is None:
                break
            await manejar_crud(conn, writer, farmacia_id, mensaje)

    except asyncio.IncompleteReadError:
        # Se lanza cuando el cliente cierra la conexión abruptamente
        # (sin mandar un cierre limpio). Es un caso esperado y normal.
        logger.info(f"Desconexión abrupta: {nombre_farmacia or direccion}")

    except Exception as e:
        logger.error(f"Error inesperado con cliente {nombre_farmacia or direccion}: {e}")

    finally:
        # El bloque finally se ejecuta SIEMPRE: haya error, return, o cierre normal.
        # Es el lugar correcto para limpiar recursos, porque garantiza que
        # nunca quedará un cliente "fantasma" en el diccionario ni una conexión abierta.
        if nombre_farmacia and nombre_farmacia.lower() in clientes_conectados:
            del clientes_conectados[nombre_farmacia.lower()]
        if farmacia_id and farmacia_id in clientes_por_id:
            del clientes_por_id[farmacia_id]

        if nombre_farmacia:
            logger.info(
                f"Farmacia '{nombre_farmacia}' desconectada y removida del registro. "
                f"Clientes activos: {len(clientes_conectados)}"
            )

        if conn:
            conn.close()

        writer.close()
        await writer.wait_closed()


async def manejar_comando_monitor(conn, writer: asyncio.StreamWriter, comando: dict) -> None:
    """
    Despachador de comandos administrativos enviados por el monitor vía IPC.

    Es el análogo de manejar_crud() pero para el canal del monitor.
    Separarlo en su propia función mantiene manejar_cliente() limpio
    y hace que los dos canales (TCP de farmacias, UDS del monitor)
    sean independientes y fáciles de razonar por separado.
    """
    accion = comando.get("accion", "")

    if accion == "crear_farmacia":
        resultado = await crear_farmacia(conn, comando.get("nombre", ""))
        logger.info(f"[monitor] crear_farmacia '{comando.get('nombre')}' → {resultado['ok']}")
        await enviar_mensaje(writer, resultado)

    elif accion == "listar_farmacias":
        resultado = await listar_farmacias(conn)
        logger.info(f"[monitor] listar_farmacias → {len(resultado.get('farmacias', []))} registros")
        await enviar_mensaje(writer, resultado)

    elif accion == "renombrar_farmacia":
        resultado = await renombrar_farmacia(
            conn,
            comando.get("nombre_actual", ""),
            comando.get("nombre_nuevo", "")
        )
        logger.warning(f"[monitor] renombrar_farmacia '{comando.get('nombre_actual')}' → '{comando.get('nombre_nuevo')}': {resultado['ok']}")
        await enviar_mensaje(writer, resultado)

    elif accion == "desactivar_farmacia":
        nombre = comando.get("nombre", "")
        resultado = await desactivar_farmacia(conn, nombre)

        # Si la farmacia estaba conectada en este momento, hay que avisarle
        # y cerrar su conexión. Buscamos por nombre normalizado.
        if resultado["ok"]:
            nombre_norm = nombre.strip().lower()
            if nombre_norm in clientes_conectados:
                writer_farmacia = clientes_conectados[nombre_norm]
                try:
                    await enviar_mensaje(writer_farmacia, {
                        "tipo": "error",
                        "mensaje": "Tu farmacia fue desactivada por el administrador. Conexión cerrada."
                    })
                    writer_farmacia.close()
                    await writer_farmacia.wait_closed()
                except Exception:
                    pass  # Si ya estaba desconectada, ignoramos el error
                # La limpieza del diccionario la hace el finally de manejar_cliente
                logger.warning(f"[monitor] Farmacia '{nombre}' desactivada y desconectada del servidor.")

        logger.warning(f"[monitor] desactivar_farmacia '{nombre}' → {resultado['ok']}")
        await enviar_mensaje(writer, resultado)
    
    elif accion == "activar_farmacia":
        nombre = comando.get("nombre", "")
        resultado = await activar_farmacia(conn, nombre)
        # INFO porque reactivar una farmacia es una operación de recuperación,
        # no una acción destructiva que requiera nivel WARNING.
        logger.info(f"[monitor] activar_farmacia '{nombre}' → {resultado['ok']}")
        await enviar_mensaje(writer, resultado)

    elif accion == "estadisticas":
        resultado = await obtener_estadisticas(conn)
        logger.info("[monitor] estadisticas solicitadas")
        await enviar_mensaje(writer, resultado)

    elif accion == "status":
        # El status usa datos en memoria (clientes_conectados) más datos de BD.
        # No necesita una función de repositorio porque parte de la info
        # solo existe en el proceso del servidor, no en la BD.
        resultado = {
            "ok": True,
            "farmacias_conectadas": list(clientes_conectados.keys()),
            "total_conectadas": len(clientes_conectados)
        }
        logger.info("[monitor] status solicitado")
        await enviar_mensaje(writer, resultado)

    elif accion == "run_tarea":
        # El monitor puede forzar la ejecución inmediata de tareas de Celery.
        # Importamos acá para evitar imports circulares al inicio del módulo.
        from src.workers.tasks import verificar_vencimientos, limpiar_notificaciones_antiguas
        tarea = comando.get("tarea", "")

        if tarea == "verificar_vencimientos":
            verificar_vencimientos.delay()
            resultado = {"ok": True, "mensaje": "Tarea 'verificar_vencimientos' encolada."}
        elif tarea == "limpiar_notificaciones":
            limpiar_notificaciones_antiguas.delay()
            resultado = {"ok": True, "mensaje": "Tarea 'limpiar_notificaciones_antiguas' encolada."}
        else:
            resultado = {"ok": False, "mensaje": f"Tarea '{tarea}' no reconocida."}

        logger.info(f"[monitor] run_tarea '{tarea}' → {resultado['ok']}")
        await enviar_mensaje(writer, resultado)

    else:
        logger.warning(f"[monitor] Acción desconocida: '{accion}'")
        await enviar_mensaje(writer, {
            "ok": False,
            "mensaje": f"Acción '{accion}' no reconocida."
        })


async def manejar_conexion_monitor(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Corrutina que maneja UNA conexión del monitor por el Unix Domain Socket.

    A diferencia de manejar_cliente(), el monitor envía un comando,
    recibe la respuesta, y cierra la conexión. Es un patrón request-response
    puro, sin loop de mensajes. Esto simplifica el protocolo de IPC:
    cada invocación del monitor abre, opera, y cierra.
    """
    conn = None
    try:
        conn  = await get_async_connection()
        comando = await recibir_mensaje(reader)

        if comando is None:
            logger.warning("[monitor] Conexión IPC recibida pero sin mensaje.")
            return

        logger.info(f"[monitor] Comando recibido: {comando.get('accion', 'desconocido')}")
        await manejar_comando_monitor(conn, writer, comando)

    except asyncio.IncompleteReadError:
        logger.info("[monitor] Conexión IPC cerrada abruptamente.")

    except Exception as e:
        logger.error(f"[monitor] Error inesperado: {e}")
        try:
            await enviar_mensaje(writer, {"ok": False, "mensaje": f"Error interno del servidor: {e}"})
        except Exception:
            pass

    finally:
        if conn:
            conn.close()
        writer.close()
        await writer.wait_closed()


async def escuchar_monitor_ipc(socket_path: str):
    """
    Lanza el servidor Unix Domain Socket que escucha comandos del monitor.

    Corre como una tarea independiente en el mismo event loop que el
    servidor TCP y la escucha de Redis. Los tres conviven sin bloquearse.

    Si el archivo del socket quedó de una ejecución anterior (por ejemplo,
    si el servidor crasheó), lo eliminamos antes de crear el nuevo para
    evitar el error 'Address already in use'.
    """
    # Limpieza preventiva: si existe el archivo del socket de una sesión anterior,
    # lo eliminamos. Un socket viejo no sirve para nada y bloquearía el arranque.
    if os.path.exists(socket_path):
        os.remove(socket_path)
        logger.info(f"Socket IPC anterior eliminado: {socket_path}")

    servidor_ipc = await asyncio.start_unix_server(
        manejar_conexion_monitor,
        path=socket_path
    )
    logger.info(f"Monitor IPC escuchando en: {socket_path}")

    async with servidor_ipc:
        await servidor_ipc.serve_forever()


async def iniciar_servidor(host: str, puerto: int, socket_path: str):
    """
    Lanza el servidor TCP, el listener IPC del monitor, y la escucha
    de Redis como tareas concurrentes dentro del mismo event loop.

    Tres corrutinas corriendo en paralelo cooperativo:
      1. servidor TCP  → atiende farmacias
      2. servidor IPC  → atiende al monitor administrador
      3. escucha Redis → reenvía notificaciones a clientes conectados
    """
    servidor = await asyncio.start_server(manejar_cliente, host, puerto)
    logger.info(f"Servidor PharmaNotify escuchando en {host}:{puerto}")

    tarea_redis  = asyncio.create_task(escuchar_notificaciones_redis())
    tarea_ipc    = asyncio.create_task(escuchar_monitor_ipc(socket_path))

    async with servidor:
        await servidor.serve_forever()

    tarea_redis.cancel()
    tarea_ipc.cancel()
    for tarea in (tarea_redis, tarea_ipc):
        try:
            await tarea
        except asyncio.CancelledError:
            pass


def parsear_argumentos():
    """
    Procesa los argumentos de línea de comandos del servidor:
    --host, --puerto, y --socket para el Unix Domain Socket del monitor.
    """
    parser = argparse.ArgumentParser(
        description="PharmaNotify — Servidor TCP de notificaciones de medicamentos"
    )
    parser.add_argument(
        "--host",
        default=SERVER_HOST,
        help=f"Host donde escuchar conexiones (default: {SERVER_HOST})"
    )
    parser.add_argument(
        "--puerto",
        type=int,
        default=SERVER_PORT,
        help=f"Puerto donde escuchar conexiones (default: {SERVER_PORT})"
    )
    parser.add_argument(
        "--socket",
        default=MONITOR_SOCKET_PATH,
        help=f"Ruta del Unix Domain Socket para el monitor (default: {MONITOR_SOCKET_PATH})"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parsear_argumentos()
    asyncio.run(iniciar_servidor(args.host, args.puerto, args.socket))
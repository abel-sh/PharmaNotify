import asyncio
import argparse
import logging

from src.shared import (
    SERVER_HOST, SERVER_PORT,
    enviar_mensaje, recibir_mensaje
)
from src.db.database import get_async_connection

# ─────────────────────────────────────────────────────────────────────────────
# Logger de este módulo
# __name__ toma el nombre del módulo automáticamente (src.server.server),
# lo que permite identificar en los logs exactamente de dónde viene cada línea.
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Registro global de clientes actualmente conectados.
# Clave:  nombre normalizado de la farmacia (ej: "farmacia del centro")
# Valor:  el StreamWriter de esa conexión, para poder enviarle mensajes
#         desde cualquier parte del servidor (ej: cuando llegue una notificación)
# ─────────────────────────────────────────────────────────────────────────────
clientes_conectados: dict[str, asyncio.StreamWriter] = {}


async def obtener_resumen_estado(conn, farmacia_id: int) -> dict:
    """
    Consulta la BD y construye un resumen del estado actual de la farmacia.
    Se envía automáticamente al cliente justo después de que se valida su conexión.
    """
    async with conn.cursor() as cursor:

        # Cuántos medicamentos activos tiene esta farmacia
        await cursor.execute(
            "SELECT COUNT(*) FROM medicamentos WHERE farmacia_id = %s AND activo = TRUE",
            (farmacia_id,)
        )
        (total_activos,) = await cursor.fetchone()

        # Cuántas notificaciones todavía no leyó
        await cursor.execute(
            "SELECT COUNT(*) FROM notificaciones WHERE farmacia_id = %s AND leida = FALSE",
            (farmacia_id,)
        )
        (notificaciones_no_leidas,) = await cursor.fetchone()

        # Medicamentos que vencieron mientras la farmacia estuvo desconectada
        # (activo = FALSE porque el worker los desactivó automáticamente)
        await cursor.execute(
            """
            SELECT nombre, fecha_vencimiento
            FROM medicamentos
            WHERE farmacia_id = %s AND activo = FALSE
            ORDER BY fecha_vencimiento DESC
            LIMIT 10
            """,
            (farmacia_id,)
        )
        filas_vencidos = await cursor.fetchall()
        vencidos_lista = [
            {"nombre": fila[0], "fecha_vencimiento": str(fila[1])}
            for fila in filas_vencidos
        ]

    return {
        "tipo": "resumen_estado",
        "medicamentos_activos": total_activos,
        "notificaciones_no_leidas": notificaciones_no_leidas,
        "vencidos_mientras_ausente": vencidos_lista
    }


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

    try:
        # Recibir el primer mensaje del cliente
        # El primer mensaje que manda el cliente es simplemente su nombre de farmacia.
        mensaje_inicial = await recibir_mensaje(reader)
        nombre_farmacia_raw = mensaje_inicial.get("nombre_farmacia", "")

        # Normalizar el nombre 
        nombre_farmacia = nombre_farmacia_raw.strip().lower()

        if not nombre_farmacia:
            await enviar_mensaje(writer, {
                "tipo": "error",
                "mensaje": "Nombre de farmacia vacío. Cerrando conexión."
            })
            return  # sale del try, va directo al finally

        # Buscar la farmacia en la BD
        conn = await get_async_connection()
        async with conn.cursor() as cursor:
            # LOWER() en SQL hace lo mismo que .lower() en Python,
            # así la comparación no depende de mayúsculas en la BD.
            await cursor.execute(
                "SELECT id, nombre, activo FROM farmacias WHERE LOWER(nombre) = %s",
                (nombre_farmacia,)
            )
            farmacia = await cursor.fetchone()

        # Validar existencia y estado activo
        if farmacia is None:
            logger.warning(
                f"Intento de conexión con farmacia no registrada: "
                f"'{nombre_farmacia_raw}' desde {direccion}"
            )
            await enviar_mensaje(writer, {
                "tipo": "rechazo",
                "mensaje": f"La farmacia '{nombre_farmacia_raw}' no está registrada en el sistema."
            })
            return

        farmacia_id, farmacia_nombre, farmacia_activa = farmacia

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
        clientes_conectados[nombre_farmacia] = writer
        logger.info(
            f"Farmacia '{farmacia_nombre}' conectada exitosamente. "
            f"Clientes activos: {len(clientes_conectados)}"
        )

        resumen = await obtener_resumen_estado(conn, farmacia_id)
        await enviar_mensaje(writer, resumen)

        # Loop de escucha
        while True:
            mensaje = await recibir_mensaje(reader)
            if mensaje is None:
                break
            logger.info(f"[{farmacia_nombre}] Mensaje recibido: {mensaje}")
            # TODO 

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
        if nombre_farmacia and nombre_farmacia in clientes_conectados:
            del clientes_conectados[nombre_farmacia]
            logger.info(
                f"Farmacia '{nombre_farmacia}' removida del registro. "
                f"Clientes activos: {len(clientes_conectados)}"
            )

        if conn:
            conn.close()

        writer.close()
        await writer.wait_closed()


async def iniciar_servidor(host: str, puerto: int):
    """
    Crea el servidor TCP y lo deja escuchando indefinidamente.
    asyncio.start_server registra manejar_cliente como el callback para
    nuevas conexiones: cada vez que llega una, AsyncIO crea una tarea nueva
    que ejecuta manejar_cliente() de forma independiente.
    """
    servidor = await asyncio.start_server(
        manejar_cliente,
        host,
        puerto
    )

    logger.info(f"Servidor PharmaNotify escuchando en {host}:{puerto}")

    # "async with servidor" cierra limpiamente si el proceso recibe una señal de fin.
    # serve_forever() mantiene el event loop corriendo indefinidamente.
    async with servidor:
        await servidor.serve_forever()


def parsear_argumentos():
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
    # Nota: luego se agregará --socket para el Unix Domain Socket del monitor
    return parser.parse_args()


if __name__ == "__main__":
    args = parsear_argumentos()
    asyncio.run(iniciar_servidor(args.host, args.puerto))
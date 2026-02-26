"""
Protocolo de comunicación TCP con prefijo de longitud.

Define las funciones enviar_mensaje() y recibir_mensaje() que usan
tanto el cliente como el servidor para intercambiar diccionarios Python
por TCP. Cada mensaje se serializa como JSON y se antepone un prefijo
de 4 bytes (big-endian) con la longitud del payload.

Este módulo es la única dependencia compartida entre cliente y servidor
en cuanto a comunicación. Si el protocolo cambia, se cambia acá y
ambos extremos se adaptan automáticamente.
"""

import json
import struct

# struct.pack/unpack trabaja con el formato "!I":
#   ! = big-endian (orden de bytes estándar en redes)
#   I = unsigned int de 4 bytes (puede representar hasta ~4 GB)
LONGITUD_PREFIJO = 4


async def enviar_mensaje(writer, datos: dict) -> None:
    """
    Serializa un diccionario como JSON y lo envía por TCP
    con un prefijo de 4 bytes que indica la longitud del mensaje.

    :param writer: asyncio.StreamWriter — el canal de escritura hacia el otro extremo
    :param datos:  diccionario Python con los datos a enviar
    """
    mensaje_json = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    longitud = struct.pack("!I", len(mensaje_json))

    writer.write(longitud + mensaje_json)
    await writer.drain()


async def recibir_mensaje(reader) -> dict | None:
    """
    Lee un mensaje TCP con prefijo de longitud y lo deserializa como diccionario.
    Devuelve None si la conexión fue cerrada por el otro extremo.

    :param reader: asyncio.StreamReader — el canal de lectura desde el otro extremo
    :return: diccionario Python con los datos recibidos, o None si se cerró la conexión
    """
    # Lee exactamente 4 bytes (el prefijo con la longitud)
    prefijo = await reader.readexactly(LONGITUD_PREFIJO)
    longitud = struct.unpack("!I", prefijo)[0]

    # Lee exactamente esa cantidad de bytes (el mensaje en sí)
    datos_crudos = await reader.readexactly(longitud)
    return json.loads(datos_crudos.decode("utf-8"))

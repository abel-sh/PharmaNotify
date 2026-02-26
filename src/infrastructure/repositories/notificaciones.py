"""
Repositorio de notificaciones — operaciones asincrónicas.

Todas las funciones de este módulo son async porque las consume
exclusivamente el servidor AsyncIO. Usan aiomysql a través de
la conexión async que les pasa el servidor.
"""

async def guardar_notificacion(conn, farmacia_id: int, tipo: str, mensaje: str) -> dict:
    """
    Versión async para usar desde el servidor si fuera necesario.
    """
    async with conn.cursor() as cursor:
        await cursor.execute(
            "INSERT INTO notificaciones (farmacia_id, tipo, mensaje) VALUES (%s, %s, %s)",
            (farmacia_id, tipo, mensaje)
        )
    return {"ok": True, "mensaje": "Notificación guardada."}


async def ver_notificaciones(conn, farmacia_id: int, solo_no_leidas: bool = False) -> dict:
    """
    Consulta el historial de notificaciones y las marca como leídas.
    """
    async with conn.cursor() as cursor:
        condicion = "AND leida = FALSE" if solo_no_leidas else ""
        await cursor.execute(
            f"""
            SELECT id, tipo, mensaje, leida, creado_en
            FROM notificaciones
            WHERE farmacia_id = %s {condicion}
            ORDER BY creado_en DESC
            LIMIT 50
            """,
            (farmacia_id,)
        )
        filas = await cursor.fetchall()

        await cursor.execute(
            "UPDATE notificaciones SET leida = TRUE WHERE farmacia_id = %s AND leida = FALSE",
            (farmacia_id,)
        )

    return {
        "ok": True,
        "notificaciones": [
            {
                "id": fila[0],
                "tipo": fila[1],
                "mensaje": fila[2],
                "leida": bool(fila[3]),
                "creado_en": str(fila[4])
            }
            for fila in filas
        ]
    }
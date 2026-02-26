"""
Repositorio de notificaciones — operaciones sincrónicas.

Todas las funciones de este módulo son sync porque las consumen
exclusivamente los workers de Celery, que corren en procesos
separados sin event loop de AsyncIO.
"""


def guardar_notificacion_sync(conn, farmacia_id: int, tipo: str, mensaje: str) -> None:
    """
    Persiste una notificación en la BD usando conexión sincrónica.
    Usada por los workers de Celery después de detectar un evento
    (CRUD de medicamentos, vencimiento próximo).
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO notificaciones (farmacia_id, tipo, mensaje) VALUES (%s, %s, %s)",
            (farmacia_id, tipo, mensaje)
        )
        

def verificar_notificacion_reciente_sync(conn, farmacia_id: int, codigo_medicamento: str) -> bool:
    """
    Devuelve True si ya existe una notificación de tipo 'proximo_vencimiento'
    para este medicamento generada en las últimas 24 horas.

    Usamos LIKE '%codigo%' en el mensaje porque no guardamos el código como
    campo separado en la tabla notificaciones: está embebido dentro del texto
    del mensaje.

    Las 24 horas como ventana es una decisión de negocio..
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM notificaciones
            WHERE farmacia_id = %s
              AND tipo = 'proximo_vencimiento'
              AND mensaje LIKE %s
              AND creado_en >= NOW() - INTERVAL 24 HOUR
            """,
            (farmacia_id, f"%{codigo_medicamento}%")
        )
        (cantidad,) = cursor.fetchone()
    return cantidad > 0


def obtener_medicamentos_proximos_sync(conn) -> list:
    """
    Consulta medicamentos activos cuya fecha de vencimiento cae dentro
    del umbral configurado por cada farmacia.

    El JOIN con farmacias es necesario porque cada farmacia tiene su propio
    umbral_dias: una farmacia puede querer alertas con 7 días de anticipación
    y otra con 15. No podemos usar un valor fijo global.

    Filtramos fecha_vencimiento >= CURDATE() para excluir medicamentos ya
    vencidos, que se manejan por otro mecanismo (desactivación automática).

    Devuelve una lista de tuplas con los datos que necesita
    verificar_vencimientos para generar las alertas.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                m.farmacia_id,
                m.codigo,
                m.nombre,
                m.fecha_vencimiento,
                f.umbral_dias,
                DATEDIFF(m.fecha_vencimiento, CURDATE()) AS dias_restantes
            FROM medicamentos m
            JOIN farmacias f ON f.id = m.farmacia_id
            WHERE m.activo = TRUE
              AND f.activo = TRUE
              AND m.fecha_vencimiento <= DATE_ADD(CURDATE(), INTERVAL f.umbral_dias DAY)
              AND m.fecha_vencimiento >= CURDATE()
            ORDER BY m.fecha_vencimiento ASC
            """
        )
        return cursor.fetchall()


def limpiar_notificaciones_antiguas_sync(conn, retention_days: int) -> int:
    """
    Elimina físicamente las notificaciones que cumplen dos condiciones:
      1. Ya fueron leídas (leida = TRUE).
      2. Tienen más de retention_days días de antigüedad.

    Devuelve la cantidad de registros eliminados para el log.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM notificaciones
            WHERE leida = TRUE
              AND creado_en < NOW() - INTERVAL %s DAY
            """,
            (retention_days,)
        )
        return cursor.rowcount
async def crear_farmacia(conn, nombre: str) -> dict:
    """
    Da de alta una nueva farmacia en el sistema.
    Solo el monitor puede hacer esto: es la razón por la que el monitor existe.
    Normalizamos el nombre antes de guardarlo para que la búsqueda por LOWER()
    en manejar_cliente() siempre funcione.
    """
    nombre_normalizado = nombre.strip()

    if not nombre_normalizado:
        return {"ok": False, "mensaje": "El nombre de la farmacia no puede estar vacío."}

    async with conn.cursor() as cursor:
        # Verificamos duplicados antes de intentar el INSERT.
        # Comparamos en minúsculas para que "Farmacia Centro" y "farmacia centro"
        # se consideren la misma farmacia.
        await cursor.execute(
            "SELECT id FROM farmacias WHERE LOWER(nombre) = LOWER(%s)",
            (nombre_normalizado,)
        )
        if await cursor.fetchone():
            return {"ok": False, "mensaje": f"Ya existe una farmacia con el nombre '{nombre_normalizado}'."}

        await cursor.execute(
            "INSERT INTO farmacias (nombre) VALUES (%s)",
            (nombre_normalizado,)
        )
        farmacia_id = cursor.lastrowid

    return {"ok": True, "mensaje": f"Farmacia '{nombre_normalizado}' creada con id={farmacia_id}."}


async def listar_farmacias(conn) -> dict:
    """
    Devuelve todas las farmacias del sistema, activas e inactivas.
    El monitor necesita ver el panorama completo para administrar.
    """
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT id, nombre, umbral_dias, activo, creado_en
            FROM farmacias
            ORDER BY activo DESC, nombre ASC
            """
        )
        filas = await cursor.fetchall()

    return {
        "ok": True,
        "farmacias": [
            {
                "id": fila[0],
                "nombre": fila[1],
                "umbral_dias": fila[2],
                "activo": bool(fila[3]),
                "creado_en": str(fila[4])
            }
            for fila in filas
        ]
    }


async def renombrar_farmacia(conn, nombre_actual: str, nombre_nuevo: str) -> dict:
    """
    Renombra una farmacia activa.
    Verificamos que el nombre nuevo no esté ya en uso para evitar duplicados.
    """
    nombre_actual_norm = nombre_actual.strip()
    nombre_nuevo_norm  = nombre_nuevo.strip()

    async with conn.cursor() as cursor:
        # Buscamos la farmacia a renombrar
        await cursor.execute(
            "SELECT id FROM farmacias WHERE LOWER(nombre) = LOWER(%s) AND activo = TRUE",
            (nombre_actual_norm,)
        )
        farmacia = await cursor.fetchone()

        if not farmacia:
            return {"ok": False, "mensaje": f"No se encontró una farmacia activa con el nombre '{nombre_actual_norm}'."}

        # Verificamos que el nombre nuevo no esté tomado
        await cursor.execute(
            "SELECT id FROM farmacias WHERE LOWER(nombre) = LOWER(%s)",
            (nombre_nuevo_norm,)
        )
        if await cursor.fetchone():
            return {"ok": False, "mensaje": f"Ya existe una farmacia con el nombre '{nombre_nuevo_norm}'."}

        await cursor.execute(
            "UPDATE farmacias SET nombre = %s WHERE id = %s",
            (nombre_nuevo_norm, farmacia[0])
        )

    return {"ok": True, "mensaje": f"Farmacia renombrada de '{nombre_actual_norm}' a '{nombre_nuevo_norm}'."}


async def desactivar_farmacia(conn, nombre: str) -> dict:
    """
    Desactiva lógicamente una farmacia (activo = FALSE).
    No la elimina físicamente: mantiene el historial de medicamentos
    y notificaciones intacto.
    """
    nombre_norm = nombre.strip()

    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT id FROM farmacias WHERE LOWER(nombre) = LOWER(%s) AND activo = TRUE",
            (nombre_norm,)
        )
        farmacia = await cursor.fetchone()

        if not farmacia:
            return {"ok": False, "mensaje": f"No se encontró una farmacia activa con el nombre '{nombre_norm}'."}

        await cursor.execute(
            "UPDATE farmacias SET activo = FALSE WHERE id = %s",
            (farmacia[0],)
        )

    return {"ok": True, "farmacia_id": farmacia[0], "mensaje": f"Farmacia '{nombre_norm}' desactivada."}


async def obtener_estadisticas(conn) -> dict:
    """
    Consulta estadísticas generales del sistema para el monitor.
    Una sola función que agrega datos de múltiples tablas para
    no dispersar consultas de estadística por todo el código.
    """
    async with conn.cursor() as cursor:

        await cursor.execute("SELECT COUNT(*) FROM farmacias WHERE activo = TRUE")
        (farmacias_activas,) = await cursor.fetchone()

        await cursor.execute("SELECT COUNT(*) FROM medicamentos WHERE activo = TRUE")
        (medicamentos_activos,) = await cursor.fetchone()

        # Medicamentos que vencen en los próximos 7 días (umbral global de referencia)
        await cursor.execute(
            """
            SELECT COUNT(*) FROM medicamentos
            WHERE activo = TRUE
              AND fecha_vencimiento BETWEEN CURDATE()
              AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            """
        )
        (proximos_a_vencer,) = await cursor.fetchone()

        # Notificaciones generadas hoy
        await cursor.execute(
            "SELECT COUNT(*) FROM notificaciones WHERE DATE(creado_en) = CURDATE()"
        )
        (notificaciones_hoy,) = await cursor.fetchone()

    return {
        "ok": True,
        "farmacias_activas": farmacias_activas,
        "medicamentos_activos": medicamentos_activos,
        "proximos_a_vencer": proximos_a_vencer,
        "notificaciones_hoy": notificaciones_hoy
    }


async def configurar_umbral(conn, farmacia_id: int, umbral_dias: int) -> dict:
    """
    Actualiza el umbral de días de anticipación para alertas de vencimiento.
    Separamos la verificación de existencia del update porque MariaDB reporta
    rowcount = 0 cuando el valor nuevo es igual al actual, lo que haría
    imposible distinguir entre "farmacia no encontrada" y "valor sin cambios".
    """
    async with conn.cursor() as cursor:

        # Primero verificamos que la farmacia existe y está activa.
        # Esta consulta es independiente del valor de umbral_dias,
        # así que siempre nos dice la verdad sobre si la farmacia existe.
        await cursor.execute(
            "SELECT umbral_dias FROM farmacias WHERE id = %s AND activo = TRUE",
            (farmacia_id,)
        )
        fila = await cursor.fetchone()

        if fila is None:
            return {"ok": False, "mensaje": "Farmacia no encontrada o inactiva."}

        umbral_actual = fila[0]

        # Si el valor nuevo es igual al actual, lo informamos amigablemente
        # en lugar de hacer un UPDATE innecesario.
        if umbral_actual == umbral_dias:
            return {
                "ok": True,
                "mensaje": f"El umbral ya estaba configurado en {umbral_dias} días. No se realizaron cambios."
            }

        # Solo llegamos acá si el valor realmente cambió.
        await cursor.execute(
            "UPDATE farmacias SET umbral_dias = %s WHERE id = %s AND activo = TRUE",
            (umbral_dias, farmacia_id)
        )

    return {"ok": True, "mensaje": f"Umbral actualizado de {umbral_actual} a {umbral_dias} días."}
"""
Repositorio de operaciones sobre la tabla 'farmacias'.

Todas las funciones son async porque las consume exclusivamente
el servidor AsyncIO a través de la capa de infraestructura.
Encapsula: alta, baja lógica, renombrado, activación, configuración
de umbral, búsqueda por nombre, estadísticas y resumen de estado.
"""

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


async def buscar_farmacia_por_nombre(conn, nombre: str) -> dict:
    """
    Busca una farmacia por nombre normalizado para validar conexiones de clientes.
    Devuelve la info necesaria para que el servidor decida si aceptar o rechazar
    la conexión, sin que el servidor tenga que conocer la estructura de la tabla.

    A diferencia de las otras funciones de este repositorio, esta NO filtra
    por activo = TRUE porque el servidor necesita distinguir tres casos:
    farmacia no existe, farmacia desactivada, y farmacia activa.
    """
    nombre_normalizado = nombre.strip()

    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT id, nombre, activo FROM farmacias WHERE LOWER(nombre) = LOWER(%s)",
            (nombre_normalizado,)
        )
        fila = await cursor.fetchone()

    if fila is None:
        return {"ok": False, "encontrada": False}

    return {
        "ok": True,
        "encontrada": True,
        "farmacia_id": fila[0],
        "nombre": fila[1],
        "activa": bool(fila[2])
    }

async def activar_farmacia(conn, nombre: str) -> dict:
    """
    Reactiva una farmacia que estaba desactivada (activo = TRUE).
    Es el espejo exacto de desactivar_farmacia: misma lógica de
    distinción de casos, dirección opuesta.
    Si la farmacia no existe, ya estaba activa, o se reactiva ahora,
    cada caso recibe su propio mensaje.
    """
    nombre_norm = nombre.strip()

    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT id, activo FROM farmacias WHERE LOWER(nombre) = LOWER(%s)",
            (nombre_norm,)
        )
        farmacia = await cursor.fetchone()

        if farmacia is None:
            return {"ok": False, "mensaje": f"No existe ninguna farmacia con el nombre '{nombre_norm}'."}

        farmacia_id, esta_activa = farmacia

        if esta_activa:
            return {"ok": False, "mensaje": f"La farmacia '{nombre_norm}' ya estaba activa."}

        await cursor.execute(
            "UPDATE farmacias SET activo = TRUE WHERE id = %s",
            (farmacia_id,)
        )

    return {"ok": True, "farmacia_id": farmacia_id, "mensaje": f"Farmacia '{nombre_norm}' reactivada exitosamente."}


async def desactivar_farmacia(conn, nombre: str) -> dict:
    """
    Desactiva lógicamente una farmacia (activo = FALSE).
    Distingue entre tres casos posibles: no existe, ya estaba inactiva,
    o estaba activa y se desactiva ahora. Esto le da al administrador
    feedback honesto en lugar del genérico "no encontrada".
    """
    nombre_norm = nombre.strip()

    async with conn.cursor() as cursor:
        # Buscamos sin filtrar por activo para poder distinguir los casos.
        await cursor.execute(
            "SELECT id, activo FROM farmacias WHERE LOWER(nombre) = LOWER(%s)",
            (nombre_norm,)
        )
        farmacia = await cursor.fetchone()

        if farmacia is None:
            return {"ok": False, "mensaje": f"No existe ninguna farmacia con el nombre '{nombre_norm}'."}

        farmacia_id, esta_activa = farmacia

        # Si ya estaba inactiva, informamos sin hacer el UPDATE innecesario.
        # El mismo patrón que usamos en configurar_umbral cuando el valor no cambia.
        if not esta_activa:
            return {"ok": False, "mensaje": f"La farmacia '{nombre_norm}' ya estaba desactivada."}

        await cursor.execute(
            "UPDATE farmacias SET activo = FALSE WHERE id = %s",
            (farmacia_id,)
        )

    return {"ok": True, "farmacia_id": farmacia_id, "mensaje": f"Farmacia '{nombre_norm}' desactivada."}


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


async def obtener_resumen_farmacia(conn, farmacia_id: int) -> dict:
    """
    Consulta la BD y construye un resumen del estado actual de la farmacia.
    Se envía automáticamente al cliente justo después de que se valida su conexión.
    """
    async with conn.cursor() as cursor:

        await cursor.execute(
            "SELECT COUNT(*) FROM medicamentos WHERE farmacia_id = %s AND activo = TRUE",
            (farmacia_id,)
        )
        (total_activos,) = await cursor.fetchone()

        await cursor.execute(
            "SELECT COUNT(*) FROM notificaciones WHERE farmacia_id = %s AND leida = FALSE",
            (farmacia_id,)
        )
        (notificaciones_no_leidas,) = await cursor.fetchone()

        # Ahora el filtro es preciso: solo medicamentos desactivados
        # automáticamente por Celery cuando su fecha de vencimiento pasó.
        # Los eliminados manualmente por el usuario tienen motivo_baja = 'eliminado_manual'
        # y no tienen nada que hacer en esta sección del resumen.
        await cursor.execute(
            """
            SELECT nombre, fecha_vencimiento
            FROM medicamentos
            WHERE farmacia_id = %s 
              AND activo = FALSE 
              AND motivo_baja = 'vencido_automatico'
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
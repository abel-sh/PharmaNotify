import aiomysql
import pymysql
from src.shared import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


# =============================================================================
# Conexión ASYNC — para el servidor AsyncIO
# =============================================================================

async def get_async_connection():
    """
    Devuelve una conexión async a MariaDB.
    Usada por el servidor para no bloquear el event loop mientras espera la BD.
    """
    conexion = await aiomysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        autocommit=True
    )
    return conexion

# =============================================================================
# Conexión SYNC — para los workers de Celery
# =============================================================================

def get_sync_connection():
    """
    Devuelve una conexión sync a MariaDB.
    Usada por los workers de Celery, que no corren en un event loop.
    """
    conexion = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True
    )
    return conexion

# =============================================================================
# Operaciones CRUD — Medicamentos (async, para el servidor)
# =============================================================================

async def crear_medicamento(conn, farmacia_id: int, codigo: str, nombre: str, fecha_vencimiento: str) -> dict:
    """
    Inserta un nuevo medicamento para la farmacia dada.
    Devuelve un dict con "ok" True/False y un "mensaje" descriptivo.
    La constraint UNIQUE(farmacia_id, codigo) en la BD impide duplicados.
    """
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO medicamentos (farmacia_id, codigo, nombre, fecha_vencimiento)
                VALUES (%s, %s, %s, %s)
                """,
                (farmacia_id, codigo, nombre, fecha_vencimiento)
            )
        return {"ok": True, "mensaje": f"Medicamento '{nombre}' creado correctamente."}

    except Exception as e:
        # El error más común acá es una violación de la constraint UNIQUE.
        # aiomysql lanza un error con código 1062 para duplicados.
        if "1062" in str(e):
            return {"ok": False, "mensaje": f"Ya existe un medicamento con el código '{codigo}' para esta farmacia."}
        return {"ok": False, "mensaje": f"Error al crear medicamento: {e}"}


async def listar_medicamentos(conn, farmacia_id: int) -> dict:
    """
    Devuelve todos los medicamentos activos de la farmacia.
    """
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT codigo, nombre, fecha_vencimiento
            FROM medicamentos
            WHERE farmacia_id = %s AND activo = TRUE
            ORDER BY fecha_vencimiento ASC
            """,
            (farmacia_id,)
        )
        filas = await cursor.fetchall()

    medicamentos = [
        {
            "codigo": fila[0],
            "nombre": fila[1],
            "fecha_vencimiento": str(fila[2])
        }
        for fila in filas
    ]
    return {"ok": True, "medicamentos": medicamentos}


async def buscar_medicamento(conn, farmacia_id: int, codigo: str) -> dict:
    """
    Busca un medicamento activo por su código dentro de la farmacia.
    """
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT codigo, nombre, fecha_vencimiento
            FROM medicamentos
            WHERE farmacia_id = %s AND codigo = %s AND activo = TRUE
            """,
            (farmacia_id, codigo)
        )
        fila = await cursor.fetchone()

    if fila is None:
        return {"ok": False, "mensaje": f"No se encontró el medicamento con código '{codigo}'."}

    return {
        "ok": True,
        "medicamento": {
            "codigo": fila[0],
            "nombre": fila[1],
            "fecha_vencimiento": str(fila[2])
        }
    }


async def actualizar_medicamento(conn, farmacia_id: int, codigo: str, nombre: str | None, fecha_vencimiento: str | None) -> dict:
    """
    Actualiza los campos que se hayan enviado (None significa "no cambiar").
    Construye la query dinámicamente para modificar solo lo necesario.
    """
    # Construimos la lista de campos a actualizar dinámicamente.
    # Así si el usuario no manda nombre, no lo pisamos con un valor vacío.
    campos = []
    valores = []

    if nombre:
        campos.append("nombre = %s")
        valores.append(nombre)
    if fecha_vencimiento:
        campos.append("fecha_vencimiento = %s")
        valores.append(fecha_vencimiento)

    if not campos:
        return {"ok": False, "mensaje": "No se enviaron campos para actualizar."}

    # Agregamos al final los valores del WHERE
    valores.extend([farmacia_id, codigo])

    async with conn.cursor() as cursor:
        await cursor.execute(
            f"UPDATE medicamentos SET {', '.join(campos)} WHERE farmacia_id = %s AND codigo = %s AND activo = TRUE",
            valores
        )
        # rowcount indica cuántas filas fueron afectadas por el UPDATE.
        # Si es 0, el medicamento no existía o ya estaba desactivado.
        if cursor.rowcount == 0:
            return {"ok": False, "mensaje": f"No se encontró el medicamento '{codigo}' para actualizar."}

    return {"ok": True, "mensaje": f"Medicamento '{codigo}' actualizado correctamente."}


async def eliminar_medicamento(conn, farmacia_id: int, codigo: str) -> dict:
    """
    Eliminación lógica: marca activo = FALSE y registra el motivo como
    'eliminado_manual', distinguiéndolo de los medicamentos desactivados
    automáticamente por Celery cuando vencen ('vencido_automatico').
    Así el resumen de estado puede mostrar solo los vencidos reales,
    no los que el usuario decidió sacar del inventario conscientemente.
    """
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            UPDATE medicamentos 
            SET activo = FALSE, motivo_baja = 'eliminado_manual'
            WHERE farmacia_id = %s AND codigo = %s AND activo = TRUE
            """,
            (farmacia_id, codigo)
        )
        if cursor.rowcount == 0:
            return {"ok": False, "mensaje": f"No se encontró el medicamento '{codigo}' para eliminar."}

    return {"ok": True, "mensaje": f"Medicamento '{codigo}' eliminado correctamente."}
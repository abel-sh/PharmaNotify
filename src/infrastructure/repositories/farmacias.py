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
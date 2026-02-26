"""
Funciones de presentación visual del monitor administrativo.

Separadas de la lógica del monitor por el mismo motivo que en el cliente:
los cambios de formato visual no deben tocar la lógica de comunicación IPC,
y viceversa.
"""


def mostrar_menu() -> None:
    """
    Imprime el menú interactivo del monitor con las opciones de administración.
    """
    print("\n+------------------------------------------+")
    print("|       PHARMA NOTIFY — MONITOR ADMIN      |")
    print("+------------------------------------------+")
    print("|  FARMACIAS                               |")
    print("|    1. Registrar farmacia                 |")
    print("|    2. Listar farmacias                   |")
    print("|    3. Renombrar farmacia                 |")
    print("|    4. Desactivar farmacia                |")
    print("|    5. Activar farmacia                   |")
    print("|  SISTEMA                                 |")
    print("|    6. Ver estado (conexiones activas)    |")
    print("|    7. Ver estadísticas                   |")
    print("|  TAREAS                                  |")
    print("|    8. Forzar verificación de vencimientos|")
    print("|    9. Forzar limpieza de notificaciones  |")
    print("|  ---                                     |")
    print("|   10. Salir                              |")
    print("+------------------------------------------+")
    print("|  Escribí 'cancelar' para volver          |")
    print("|  al menú desde cualquier operación       |")
    print("+------------------------------------------+")
    print("Opción: ", end="", flush=True)


def mostrar_respuesta(respuesta: dict) -> None:
    """
    Formatea e imprime la respuesta del servidor según su contenido.
    Detecta el tipo de respuesta por las claves presentes en el dict,
    igual que hace mostrar_resumen() en el cliente con el resumen de estado.
    """
    if not respuesta.get("ok"):
        print(f"\n  ✘ {respuesta.get('mensaje', 'Error desconocido.')}")
        return

    # Respuesta de listar_farmacias
    if "farmacias" in respuesta:
        farmacias = respuesta["farmacias"]
        if not farmacias:
            print("\n  No hay farmacias registradas en el sistema.")
            return
        print(f"\n  {'ID':<6} {'NOMBRE':<30} {'UMBRAL':<8} {'ACTIVA':<8} {'CREADA'}")
        print("  " + "─" * 70)
        for f in farmacias:
            activa = "Sí" if f["activo"] else "No"
            print(
                f"  {f['id']:<6} {f['nombre']:<30} "
                f"{f['umbral_dias']:<8} {activa:<8} {f['creado_en']}"
            )
        return

    # Respuesta de status
    if "farmacias_conectadas" in respuesta:
        conectadas = respuesta["farmacias_conectadas"]
        total = respuesta["total_conectadas"]
        print(f"\n  Farmacias conectadas ahora: {total}")
        if conectadas:
            for nombre in conectadas:
                print(f"    • {nombre}")
        else:
            print("    (ninguna)")
        return

    # Respuesta de estadisticas
    if "farmacias_activas" in respuesta:
        print(f"\n  Farmacias activas:        {respuesta['farmacias_activas']}")
        print(f"  Medicamentos activos:     {respuesta['medicamentos_activos']}")
        print(f"  Próximos a vencer (7d):   {respuesta['proximos_a_vencer']}")
        print(f"  Notificaciones hoy:       {respuesta['notificaciones_hoy']}")
        return

    # Respuesta genérica: cualquier comando que solo devuelva ok + mensaje
    simbolo = "✔" if respuesta.get("ok") else "✘"
    print(f"\n  {simbolo} {respuesta.get('mensaje', '')}")
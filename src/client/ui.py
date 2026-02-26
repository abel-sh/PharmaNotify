"""
Funciones de presentación visual del cliente PharmaNotify.

Separadas de la lógica del cliente para que cualquier cambio
en cómo se muestra la información no afecte la lógica de comunicación,
y viceversa.
"""

def mostrar_resumen(resumen: dict) -> None:
    """
    Muestra en pantalla el resumen de estado que envía el servidor
    justo después de que la farmacia se conecta.
    """
    print("\n+--------------------------------------+")
    print("|         RESUMEN DE ESTADO            |")
    print("+--------------------------------------+")
    print(f"  Medicamentos activos:      {resumen.get('medicamentos_activos', 0)}")
    print(f"  Notificaciones no leídas:  {resumen.get('notificaciones_no_leidas', 0)}")

    vencidos = resumen.get("vencidos_mientras_ausente", [])
    if vencidos:
        print(f"\n  ⚠ Medicamentos vencidos mientras estabas desconectado:")
        for v in vencidos:
            print(f"    - {v['nombre']} (venció: {v['fecha_vencimiento']})")
    print("+--------------------------------------+\n")


def mostrar_menu() -> None:
    """
    Imprime el menú interactivo del cliente con las opciones disponibles.
    """
    print("\n+--------------------------------------+")
    print("|           PHARMA NOTIFY              |")
    print("+--------------------------------------+")
    print("|  1. Crear medicamento                |")
    print("|  2. Listar medicamentos              |")
    print("|  3. Buscar medicamento               |")
    print("|  4. Actualizar medicamento           |")
    print("|  5. Eliminar medicamento             |")
    print("|  6. Ver notificaciones               |")
    print("|  7. Configurar umbral de alertas     |")
    print("|  8. Ver resumen de estado            |")
    print("|  9. Salir                            |")  
    print("+--------------------------------------+")
    print("|  Escribí 'cancelar' para volver      |")
    print("|  al menú desde cualquier operación   |")
    print("+--------------------------------------+")
    print("Opción: ", end="", flush=True)

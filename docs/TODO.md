# TODO — Mejoras futuras

Este documento lista mejoras y nuevas funcionalidades identificadas durante el desarrollo que quedaron fuera del alcance actual del proyecto. Están organizadas por área temática, de mayor a menor impacto sobre la confiabilidad y escalabilidad del sistema.

---

## Seguridad

**Autenticación de farmacias con tokens.** Actualmente cualquier cliente que conozca el nombre de una farmacia registrada puede conectarse haciéndose pasar por ella. Implementar un sistema de tokens (generados por el monitor al registrar la farmacia y presentados por el cliente al conectarse) cerraría este vector. Esto también habilitaría las dos mejoras siguientes, que dependen de poder verificar la identidad de quien opera.

**Autogestión de información desde el cliente.** Una vez que exista autenticación real, tiene sentido permitir que la propia farmacia modifique su nombre o configuración desde su sesión, sin necesidad de que el administrador intervenga para cada cambio menor.

**Eliminación de cuenta desde el cliente.** Actualmente desactivar una farmacia es una operación exclusiva del monitor. Esto es intencional: sin autenticación, cualquiera podría conectarse con el nombre de una farmacia existente y eliminarla junto con todo su historial. Con tokens, la eliminación desde el propio cliente sería segura y tendría sentido habilitarla.

**Rate limiting en el servidor.** Actualmente no hay ningún límite sobre la cantidad de conexiones o comandos que un cliente puede enviar. En un entorno expuesto, esto abre la puerta a usos abusivos o ataques de denegación de servicio. Implementar un límite de conexiones simultáneas por IP y un tope de comandos por unidad de tiempo protegería al servidor sin afectar el uso normal del sistema.

---

## Confiabilidad

**Manejo robusto de errores y desconexiones.** El sistema tiene una base de manejo de errores implementada — los workers usan `self.retry()` para reintentar tareas fallidas, y el servidor tiene bloques `finally` que garantizan la limpieza de conexiones. Sin embargo, hay escenarios que merecen cobertura más profunda: la caída de MariaDB o Redis mientras hay operaciones en curso, excepciones a mitad del loop de medicamentos en `verificar_vencimientos` que podrían dejar notificaciones a medias, y mensajes de error más descriptivos en el cliente y el monitor cuando el servidor no está disponible. Completar esta cobertura haría el sistema más resiliente en condiciones de producción real.

**Tests automatizados.** El proyecto actualmente no tiene ninguna suite de tests, ni unitarios ni de integración. Agregar tests unitarios para la capa de repositorios (verificando que las operaciones CRUD se comportan correctamente) y tests de integración para el protocolo TCP (verificando que el cliente y el servidor intercambian mensajes correctamente) aumentaría considerablemente la confianza en el sistema ante cambios futuros. Frameworks como `pytest` con `pytest-asyncio` para las corrutinas serían la elección natural dado el stack actual.

**Backup automático de la base de datos.** Agregar una tarea de Celery Beat programada para exportar un dump periódico de la base de datos, almacenándolo localmente o en un servicio externo. Es una mejora pequeña de implementar pero de alto valor operativo: ante una falla grave del sistema, la diferencia entre recuperar datos y perderlos depende de si existía un backup reciente.

---

## Experiencia de usuario

**Mejora visual de notificaciones en terminal.** Cuando llega una notificación mientras el usuario está escribiendo en el menú, ambas salidas conviven en el mismo stream de stdout sin coordinación, lo que puede interrumpir visualmente la entrada en curso. La solución completa requeriría una librería de control de terminal como `curses` o `rich`, que permite dividir la pantalla en regiones independientes para el menú y las notificaciones. Para el alcance actual del proyecto el comportamiento es aceptable — el mensaje llega correctamente, que es el objetivo principal.

**Notificaciones por email o mensajería.** Complementar las notificaciones en tiempo real del cliente con alertas por email o servicios de mensajería (Telegram, WhatsApp Business) para los casos en que la farmacia no está conectada al sistema pero necesita enterarse de un vencimiento crítico.

**Interfaz web.** Reemplazar o complementar el cliente CLI con una interfaz web que permita gestionar el inventario desde un navegador, con una visualización más clara del estado de los medicamentos y el historial de notificaciones.

**Exportación de reportes.** Agregar la posibilidad de exportar el inventario y el historial de notificaciones a formatos como CSV o PDF, útil para auditorías o registros regulatorios.

---

## Funcionalidades del dominio

**Soporte para múltiples sucursales.** Hoy una farmacia es una entidad única e independiente. Una cadena de farmacias con varias sucursales no tiene forma de agruparlas ni de ver reportes consolidados entre ellas. Agregar el concepto de organización o cadena por encima de la farmacia individual sería una extensión natural del modelo de datos, requiriendo una nueva tabla y ajustes en la capa de repositorios.

**Categorías de medicamentos.** El inventario actual solo registra código, nombre y fecha de vencimiento. Agregar categorías (analgésicos, antibióticos, etc.) permitiría filtrar el inventario, generar reportes por categoría, y en el futuro configurar umbrales de alerta distintos según el tipo de medicamento.

---

## Arquitectura

**Reconfiguración del intervalo de verificación en caliente.** Actualmente cambiar el `VERIFICATION_INTERVAL_SECONDS` requiere reiniciar Celery Beat para que tome efecto. Implementar un mecanismo que permita al monitor actualizar este valor en tiempo real, sin interrumpir el scheduler, haría la operación del sistema más flexible.

**Métricas y observabilidad.** El sistema actualmente tiene logging estructurado, pero no hay forma de visualizar tendencias a lo largo del tiempo. Exponer métricas (conexiones activas, tareas procesadas, errores por período) en un formato compatible con herramientas como Prometheus y Grafana permitiría monitorear el comportamiento del sistema de forma continua y detectar anomalías antes de que se conviertan en problemas.

**Separación de `server.py` en handlers especializados.** El servidor concentra toda su lógica en un único archivo, lo cual es apropiado para el tamaño actual del proyecto. Si en el futuro se agregaran más operaciones (endpoints REST, WebSockets, más comandos del monitor), la separación en archivos `handler_cliente.py` y `handler_monitor.py` con un módulo de estado compartido (`state.py`) sería el paso natural para mantener la legibilidad. La complejidad de ese refactor no se justifica hoy, pero es el camino correcto si el sistema crece.
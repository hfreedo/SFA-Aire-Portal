# Notificaciones: prueba simple desde la nube

Implementado y verificado el 26/10/2026.

## Recorrido

Laboratorio → elegir aula → Enviar aviso de prueba. La PC receptora y el Arduino
no intervienen en este ensayo. La app conserva el contrato FCM v2 y no necesita
otra APK para usarlo. El portal recuerda el aula por cuenta en esta sesión del
navegador, validando que siga perteneciendo a las aulas autorizadas. Durante la
carga inicial muestra un estado de consulta, sin falsas advertencias de desconexión
ni de ausencia de aulas antes de obtener la respuesta.

La pantalla muestra teléfonos habilitados, presupuesto disponible y el resultado:
programadas, aceptadas por FCM, recibidas por la app y abiertas. Sin destinatarios,
autorización o presupuesto se informa la causa y no se programa un envío parcial.
Los reintentos de la misma solicitud no duplican avisos; hay un intervalo mínimo
entre pruebas nuevas. Los errores permanecen visibles al actualizar el diagnóstico.
El seguimiento termina o marca vencimiento; un fallo del worker no deja una prueba
pendiente indefinidamente. El emisor conserva sus reintentos y clasifica errores.

La simulación completa con PC se mantiene dentro del apartado Avanzado. Esa opción
sí comprueba adquisición, persistencia e histéresis. La prueba rápida es un aviso
manual con datos sintéticos; no acredita hardware ni un evento ambiental real.
El origen cloud de pruebas está separado del origen físico, sin modificar secretos,
aula, última secuencia o contacto de la PC. No consume un cupo de PC ni ofrece
credenciales descargables. No se altera el historial ya existente.

## Acceso y consumo

Los RPC aire_send_test_alert y aire_notification_test_panel comprueban admin del
aula en servidor. El destinatario se obtiene de membresías y registros Android
con consentimiento de simulación; el navegador no elige tokens arbitrarios.
Los helpers privados no tienen EXECUTE para roles de aplicación. No se exponen
claves ni tokens. Se conservan reservas 80 operativas / 20 simuladas, doce pruebas
por día y las guardas de almacenamiento, respuestas e invocaciones. No se vincula
Billing ni se agregan servicios pagos. La fuente de documentación técnica fue
[Funciones de base de datos de Supabase](https://supabase.com/docs/guides/database/functions).

## Evidencia

PRUEBA_PUSH_SIMPLE_REAL.json registra un envío real en Sala 3ro. BTI: un intento,
aceptación FCM, recepción a los 5,098 segundos y apertura confirmada por la app.
No se solicitó una nueva confirmación humana de lo visto en pantalla. No se tomó
este ensayo individual como garantía de entrega ni como prueba física multisensor.

Pasaron 38 comprobaciones SQL específicas, nueve pruebas del worker con transportes
simulados, noventa Python, regresiones de receptores/administración/distribución y
build web. La revisión de navegador cubrió 1440/390/320, falta de teléfonos, errores,
idempotencia y la diferencia entre aceptación y recepción. Capturas y comprobaciones:
artifacts/notificaciones-simples/, artifacts/quick-notification-web/ y
artifacts/quick-notification-sql.json. Se activó la migración
simple_cloud_notification_test y aire-push versión 3. La revisión de seguridad no
añadió categorías de advertencias; se incorporaron los dos RPC autenticados previstos.

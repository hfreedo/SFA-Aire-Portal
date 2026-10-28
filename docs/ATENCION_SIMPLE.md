# SFA Aire: medir, notificar y facilitar la atención

Decisión de producto del usuario, 26/10/2026. Este criterio reemplaza las propuestas
anteriores que hacían obligatoria la coordinación para cerrar un incidente.

## Recorrido principal

1. El sensor o una simulación explícita produce una medición.
2. Las reglas existentes detectan una variación y preparan la notificación.
3. El teléfono recibe el aviso; la persona revisa el aula y decide cómo actuar.
4. Si lo desea, marca el aviso como **atendido**, con nota opcional.

La persona puede usar su comunicación habitual. **Compartir aviso** es una ayuda:
abre el selector de aplicaciones del teléfono/navegador o copia el texto cuando
el navegador lo permite. Elegir destinatario, enviar y responder ocurren en ese
canal. Cancelar no cambia el aviso. No se integra un chat cloud adicional.

No se exige coordinador, turno, códigos, indicaciones, confirmación de comprensión,
registro de resultados ni contacto con otra cuenta. La notificación y la consulta
no dependen de completar la atención. No hay pasos de comunicación que desbloqueen
el cierre ni un archivo especial por retiro del receptor.

## Atención y medición son independientes

**Atendido** significa que alguien dio por atendido ese aviso. El estado del sensor
continúa visible, incluso si sigue en alerta o no hay datos actuales. No se fabrica
normalización ni se confirma una acción realizada por otra persona.

Docentes y administradores del aula pueden atender. Observadores solo consultan;
una cuenta ajena o anónima no puede modificar avisos. El servidor conserva actor,
fecha y revisión para evitar sobrescrituras. Ante un error el formulario conserva
la nota, permite reintentar y bloquea el doble envío mientras está guardando.

## Implementación y compatibilidad

- Portal: se retira Coordinación de navegación y accesos del monitoreo. Avisos
  reúne Pendientes / Atendidos / Todos, una acción de atención y compartir opcional.
- Android: Avisos usa capacidades verificadas del servidor. Se elimina la consulta
  obligatoria a aire_coord_panel y la pantalla no presenta instrucciones ni turnos.
- PC/LAN: misma nota opcional y cierre humano independiente de la lectura.
- SQL: la migración 20261026091353_simplify_alert_attention.sql conserva la firma
  aire_attention y los valores resolver/resuelto para compatibilidad de transporte.
  El overview y estado PC anuncian attention_contract=2. El cierre nuevo añade
  closure_kind=atendido, closed_by, closed_at y closure_reason. La nota incluye una
  aclaración para lectores antiguos. El archivo administrativo previo queda como
  historial/compatibilidad, fuera del recorrido nuevo.
- Las instrucciones antiguas incompletas se retiran conservando sus contenidos,
  sin registrarlas como realizadas. Atender no crea mensajes de coordinación.
- Se mantienen Auth, permisos por aula, aislamiento de sesiones/teléfonos,
  simulación admin y guardas Free/Spark. Firmware y protocolo serial no cambian.

## Verificación y estado de entrega

Comprobación local: pruebas de integración Python, SQL PGlite de atención sencilla,
permisos y receptores, build web, recorridos reales del navegador a 1440/390/320 px,
assembleDebug, pruebas JVM y formularios ejecutados en emulador. Las pruebas web
interceptan endpoints; las de SQL usan red/Vault/cron ficticios, sin FCM real.

Evidencias: artifacts/simple-attention-sql-report.json,
artifacts/simple-attention-web/verification.json y capturas,
artifacts/android-screens-audit/ y artifacts/atencion-simple-avance.json.

**Activado en Supabase el 26/10/2026:** capacidades/ciclo de receptores y atención
sencilla. Contrato 2 y cierre vacío verificados con rol authenticated en una
transacción revertida; los cuatro avisos y su historial se conservaron. Evidencia:
artifacts/cloud-attention-activation.json. Pulse Actualizar en el portal.

**Pendiente de entrega:** aplicar las migraciones de vínculo push y ciclo del
teléfono, desplegar el emisor compatible y
distribuir la APK nueva como un conjunto validado. No reemplazar la APK histórica
0.6.2 por el APK de desarrollo ni afirmar que estos cambios ya están en el A02.
Después corresponde verificar cuentas/recepción real y montaje físico por separado.
La corrección de atención ya está desplegada en nube; no envió mensajes reales
ni dejó cierres de prueba persistidos.

# SFA Aire 0.8.0 — interfaz y usabilidad

27/10/2026. Implementación del plan de revisión con Impeccable, refactoring-ui y
ux-heuristics. Se conserva el verde/salvia y la arquitectura del sistema.

## Cambios aplicados

**Android:** Mi aula separa contexto, estado y mediciones. Temperatura y MQ135
tienen valores mayores, superficies claras y altura compartida; con letra
ampliada se apilan. La ayuda de sensores queda junto al título Mediciones.
La fecha exacta se puede consultar desde la antigüedad de la lectura. Simulación
y datos vencidos conservan etiquetas explícitas y valores históricos distinguibles.

Avisos usa una sola cabecera de sección y contexto de aula. Marcar atendido
ejecuta directamente la acción autorizada; Atender con nota es opcional.
Compartir sigue siendo independiente. Las capacidades verificadas, revisión del
incidente y generación de sesión siguen controlando las acciones.

Ajustes resume el estado del teléfono. La activación se muestra cuando falta
registro; el guardado de la preferencia de simulación aparece al cambiarla.
La actualización manual del registro queda en Detalles. Si existe un registro
de esta sesión para otra aula, se muestra el nombre correspondiente y no se
presenta el aula seleccionada como registrada.

Se diferencian tarjetas, campos, botones, etiquetas y diálogos; los menús de
aulas usan filas y marca de selección. Cancelar y los detalles tienen menor
peso que la acción principal. El interruptor conserva la geometría de Android
y distingue su posición apagada. La navegación usa una transición total de
240 ms y selección de 220 ms; los detalles, 200 ms. Eliminar animaciones evita
el movimiento. Las mediciones se actualizan sin reconstruir la pantalla.

**Portal:** un fallo de render/carga diferida queda contenido con explicación,
Volver a Mis aulas y Recargar portal. La navegación permanece disponible.
No hay recarga automática ni reintento automático de operaciones. El HTML local
usa no-store para reducir mezcla entre documentos y assets de diferentes builds.

Se compactan cabecera y banda DEMO, se elimina el título duplicado de Avisos y
el hover de elevación de sensores que no eran pulsables. Arduino y Personas en
DEMO dejan de pedir comprobaciones que esa vista no ejecuta. Se conserva la
prueba cloud rápida existente y las comprobaciones de permisos del backend.

## Validación

- Android assembleDebug, 39 pruebas unitarias y suite instrumentada nativa:
  sesiones, límites de entrada, formularios, actualización en sitio, vigencia,
  preferencia explícita, aviso de otra aula y atención directa sin nota obligatoria.
- Selector: seleccionar/cancelar; navegación con posiciones intermedias; prueba
  separada con animaciones desactivadas. No es una medida de FPS físico.
- Recorrido de la APK final en AVD API 30 a 360 × 800 dp, letra al 100 % y 130 %.
  Capturas y grabación nativas, no un mockup web de Android.
- 103 pruebas Python y builds web local/hosting correctos.
- Fallo de precarga del laboratorio provocado en servidor local de QA: aparece
  recuperación; Volver a Mis aulas funciona; tras restablecer recursos y recargar,
  el laboratorio abre normalmente.
- Portal revisado en escritorio y con viewports web reales de 360 y 565 px
  dentro de iframes de QA que cargan el build sin modificar sus pantallas.
- Selector Origen: End/Enter cambia a Simulación; Home/Escape conserva la
  selección anterior. No se envían avisos en estos recorridos DEMO.
- Detectores mecánicos sobre PortalBoundary y RemoteWorkspace: sin hallazgos.
  No se ejecutan detectores DOM sobre Kotlin ni se deduce calidad de ese resultado.
- Hosting estático publicado y comprobado en el navegador online, sin cambios
  de IAM/Billing ni servicios adicionales.
- La entrega se empaqueta por lista permitida y se escanea contra claves privadas,
  sesiones y datos locales. El portable incluye la APK declarada en su manifiesto.

La evidencia de la entrega está en VALIDACION_ANDROID_080.json y
VALIDACION_PORTABLE_080.json, junto a los archivos y sus hashes. La firma Android
sigue siendo la debug de las versiones piloto anteriores; permite actualizar
sobre esas versiones compatibles. No se presenta como firma de producción.

## Evidencia visual

En el entorno local de desarrollo, Branding/UX/implementacion-080 conserva capturas del build web y la APK ejecutada.
El informe HTML compara Android 0.7.4 con 0.8.0. Las pantallas con cuenta de
ejemplo/registro confirmado y otra aula son fixtures del componente real con
callbacks aislados: no prueban un registro en la nube. La grabación DEMO usa
velocidad original y no acredita rendimiento en el Samsung.

## Límites y pendientes que se conservan

1. Ensayo de esta APK en Samsung A02: teclado, pulsación, notificación real,
   apertura y fluidez. Las pruebas actuales son en emulador y no envían FCM real.
2. Verificar cobertura real con dos cuentas y dos aulas. La mejora muestra la
   vinculación efectiva conocida; no agrega suscripción automática multiaula.
3. Medición física de los sensores, acondicionamiento/referencia MQ135 y prueba
   de desconexión USB/red. Esta entrega no modifica el firmware.
4. Revisión ampliada de TalkBack, zoom web al 200 %, tema oscuro y tablets.
   La app conserva su tema claro y no declara soportar un tema oscuro nuevo.

Se implementan A–F del plan dentro del alcance descrito y se prepara G como
entrega verificable. Los pendientes anteriores no se marcan completos por
compilar, por pasar fixtures o por observar una animación interpolada.

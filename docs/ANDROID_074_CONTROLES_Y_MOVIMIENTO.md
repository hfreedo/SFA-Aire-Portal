# Android 0.7.4 · Controles coherentes y movimiento visible

Se revisan los controles que conservaban apariencia estándar de Android:

- Selector del aula con borde salvia, flecha vectorial y cuadro de selección
  propio: filas redondeadas, selección teñida y marca de verificación. Cancelar
  conserva el aula; elegir confirma sólo la selección local.
- Tema común para controles nativos: acento verde, texto oscuro y fondo marfil.
- Interruptor de simulaciones con pista verde al encender y neutra al apagar,
  círculo blanco y estados deshabilitados diferenciados.
- Campos con borde de foco coherente; diálogos de sensores, atención y conexión
  local con título, fondo y botones del mismo sistema visual.
- Desplegables con cabecera ligera y flecha giratoria, reemplazando los botones
  grandes con signos +/−. El cuerpo se expande y aparece progresivamente.

## Movimiento

La navegación mantiene sus vistas y desplaza un indicador salvia entre pestañas
durante 300 ms. El contenido sale en 90 ms y entra en 270 ms con desplazamiento
horizontal breve y fundido; no se aplica a cada lectura ni ejecuta bucles.
Las pulsaciones tienen respuesta de escala y ripple. Los desplegables usan 260 ms.

Se respeta la configuración Android: si las animaciones están desactivadas, el
cambio de pantalla se realiza directamente. No se fuerzan ajustes del teléfono.
Se conservan los bloqueos de acciones durante solicitudes, la posición de lectura
y las verificaciones de sesión/rol; no se añade una condición para atender avisos.

## Evidencia

`StyleMotionChecks` ejecuta el componente real del selector con callbacks ficticios,
comprueba cancelar y seleccionar y observa valores intermedios de opacidad,
desplazamiento del contenido e indicador. Incluye un recorrido con animaciones
activas y otro con animaciones desactivadas en el AVD propio.

El recorrido visual cubre las tres pestañas con letra normal y al 130 %. Las pruebas
previas de sesión, recepción local, permisos y formularios se mantienen. Capturas,
registro de instrumentación y grabación DEMO en `artifacts/android-074/`.
El informe publicado identifica la APK comprobada y los resultados concretos.

APK piloto 0.7.4, versionCode 13, mismo identificador y certificado. Instalar encima
de la versión anterior. Sin cambios de firmware, API, reglas, cuotas ni servicios
cloud. Continúa pendiente la prueba visual y FCM real de esta versión en el A02.

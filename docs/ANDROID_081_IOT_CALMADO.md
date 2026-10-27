# Android 0.8.1 · IoT calmado

27/10/2026. Refinamiento de la interfaz Android de 0.8.0: se separa la marca de
los colores que identifican datos, controles y estados. El portal y el portable
Windows continúan en 0.8.0; esta APK se distribuye por separado.

## Qué cambia

- Fondo neutro, superficies blancas, texto carbón y apoyo gris. Bordes de tarjeta
  suaves; campos y botones de contorno tienen borde propio, más perceptible.
- Verde/teal para la acción principal y selección. Navegación inactiva gris;
  los controles deshabilitados usan gris por estado, sin alfa sobre el verde.
- Temperatura con acento cobre, MQ135 con teal y humedad con azul. Se colorean
  iconos y pequeños soportes, no las cifras ni toda la pantalla. Son categorías
  de sensores, no un indicador de riesgo o de calidad sanitaria.
- Simulación lavanda; aviso ámbar; alerta ladrillo. La severidad y el estado
  pendiente se expresan también con texto. La tarjeta de un aviso ya no necesita
  un gran fondo amarillo para comunicar su estado.
- Acciones opcionales con iconos propios y texto neutro; acción principal rellena;
  detalles con chevron. Notificaciones y Cuenta tienen encabezados reconocibles.
- Fecha y decimales en es-PY, coherentes con los textos españoles. La hora se
  muestra en la zona horaria del dispositivo.

No cambia el recorrido de atención directa, la nota opcional, permisos, registro
FCM, contratos, firmware ni consultas cloud. Se mantienen las transiciones breves
de 0.8.0, Eliminar animaciones y la actualización de valores en su lugar.

Sistema visual: [android_app/DESIGN.md](../android_app/DESIGN.md).

## Comprobación

- assembleDebug, 39 pruebas unitarias y suite instrumentada nativa correctos.
- Recorrido en emulador API 30 a 360 × 800 dp, letra 100 % y 130 %: acceso,
  aula, avisos, ajustes, detalles y regreso. Sin recortes en las etiquetas revisadas.
- Selector, guardar preferencia, registro de otra aula, atención directa, nota
  opcional y conservación del formulario ante fallo: fixtures sin llamadas cloud.
- Movimiento normal y reducido comprobados; grabación nativa a velocidad original.
- Contrastes: texto principal 13,49:1; apoyo 6,30:1; acción principal 6,15:1;
  simulación 5,68:1; aviso 6,08:1; alerta 5,72:1; borde de control 3,21:1.
  La tabla de pares revisados se guarda en el informe local. No es una auditoría
  exhaustiva de accesibilidad ni de todas las pantallas posibles.
- APK escaneada contra secretos locales/valores privados y claves privilegiadas.
  La firma sigue siendo la debug de los pilotos anteriores.

Las capturas en Branding/UX/refinamiento-iot-081 proceden de la APK ejecutada.
El aviso habilitado y el registro confirmado son fixtures del componente real,
con datos/callbacks ficticios. No acreditan registro ni recepción real de FCM.
El informe compara pantallas DEMO en las mismas condiciones de tamaño y fuente.

Pendientes: ensayo de esta APK en Samsung A02, fluidez física, accesibilidad
ampliada y recepción FCM real. No se modifica el firewall; la descarga recomendada
para este equipo es el enlace HTTPS/QR de GitHub elegido por el usuario.

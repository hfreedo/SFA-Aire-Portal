# Android 0.7.3 · Refinamiento de la interfaz

APK piloto, versionCode 12. Misma aplicación y certificado que 0.7.2; se instala
como actualización. No incluye sesiones ni credenciales privadas de otras instalaciones.

## Composición

- Cabecera compacta y estado de actualización de la app sin franja dominante.
  La antigüedad del sensor se informa aparte, dentro de su estado ambiental.
- Un único nombre/selector del aula. El selector abre una lista con nombres
  completos; no cambia permisos, identidad de PC ni destino del teléfono.
- Temperatura y señal MQ135 con valor y unidad juntos, iconos más discretos y
  humedad en fila. Con letra ampliada las tarjetas se apilan.
- Datos vencidos: etiqueta visible, aclaración de su carácter histórico,
  tarjetas neutras y edad legible en minutos, horas o días. Tocar la antigüedad
  permite consultar la fecha exacta. MQ135 sigue siendo ADC y relación relativa.
- Avisos con origen, estado, aula y fecha; atención directa y compartir opcional.
  Entregas en un desplegable; errores y omisiones por cuota siguen visibles.
- Ajustes centrados en el estado del teléfono. Un registro confirmado con permiso
  Android se presenta como activo; actualizarlo queda como acción secundaria.
  Cambiar la preferencia de simulaciones exige guardar explícitamente.
- Navegación inferior con indicador pequeño, tipografía legible y área táctil amplia.

## Movimiento y actualización

Entrada a las pestañas con fundido/desplazamiento de 200 ms, desplegables de
180 ms y respuesta ripple de los botones. Se respeta la desactivación de animaciones
del sistema. Sin bucles, desenfoques ni animaciones decorativas permanentes.

Las nuevas mediciones se enlazan a las vistas existentes si la estructura del
aula sigue igual. No se recrea toda la pantalla por cada muestra. Cuando cambian
permisos, aulas o avisos se reconstruye lo necesario y se conserva el scroll.
Cada pestaña conserva su posición; la primera entrada al entorno empieza arriba.
Se conserva la autorización por sesión y capacidades verificadas en servidor.

## Verificación

Build `assembleDebug`, 39 pruebas unitarias Android y APK de instrumentación.
En el AVD propio API 30 se ejecutan pruebas de sesión, permisos, formularios,
contrato local y vistas: reutilización de componentes al actualizar muestras,
antigüedad/vencimiento, registro confirmado ficticio y guardado explícito de
preferencias. No se autentica una cuenta real ni se envían mensajes cloud.

El recorrido visual con datos DEMO cubre Mi aula, Avisos y Ajustes con letra al
100 % y 130 %. Hay capturas privadas de QA en `artifacts/android-073/`.
No equivale a una prueba de rendimiento o FCM en el Samsung A02.

El informe y SHA-256 acompañan la descarga Android. La APK mantiene firma debug
de piloto. Supabase Free y Firebase Spark, reglas, firmware y contratos no cambian.

Windows portable 0.7.3 conserva la APK 0.7.2 incluida en su ZIP ya publicado.
Android 0.7.3 se distribuye por separado. El panel de la carpeta de desarrollo
ofrece la nueva APK mediante su manifiesto local actualizado.

# Ajuste de referencia y calibración experimental del MQ135

Disponible en el panel local: **Conexión Arduino → Calibración del MQ135**, sólo con cuenta administradora del aula asignada a esta PC.

## Observaciones iniciales

Se muestran los rangos reportados por el usuario: habitual 70–100 ADC y máximos 270–315 ADC, en unas diez pruebas. Son observaciones preliminares; no se han clasificado los máximos por condición de exposición. El punto medio 85 ADC se ofrece como referencia provisional, no como medición calibrada.

Con multiplicadores 1,30 y 1,60, 85 ADC equivale aproximadamente a aviso desde 111 ADC y alerta desde 136 ADC. Los multiplicadores, persistencia e histéresis siguen siendo configurables en las reglas existentes. Los valores ADC no equivalen a CO₂, AQI, ppm o una clasificación sanitaria.

## Captura de referencia

- Duración: 1, 3 o 5 minutos. Recibe las muestras del firmware real; no cuenta refrescos de pantalla como nuevas muestras.
- Requiere USB activo, una muestra de menos de diez segundos, fuente real y señal de estabilización del firmware. Esa señal no certifica el acondicionamiento del fabricante.
- Rechaza simulación y muestras fuera de 10–900 ADC, límites de referencia del modelo existente. Si hay menos de veinte muestras válidas, no permite aplicar el resultado.
- Propone la mediana. Muestra mínimo, máximo, número de muestras y variación central P10–P90 relativa a la mediana. Una variación superior al 35 % genera una recomendación de revisar las condiciones, no una certificación de estabilidad ni de calidad del aire.
- La referencia no cambia al iniciar ni al completar la captura: se aplica explícitamente mediante su botón.
- El DHT no es requisito para capturar la señal MQ135. Su funcionamiento y los estados de diagnóstico del sistema se mantienen independientes del cálculo de referencia.

## Ajuste manual e historial

Es posible introducir una referencia entre 10 y 900 ADC y previsualizar los umbrales en ADC. La confirmación de acondicionamiento conserva su significado previo: no se activa automáticamente al elegir 85 ADC. Las reglas experimentales de las simulaciones mantienen su referencia independiente de 300 ADC.

Cada cambio de referencia o preparación guarda una versión previa; se conservan cinco, por aula de la PC. Una referencia anterior puede recuperarse sin cambiar la configuración de temperatura ni atender incidentes. Guardado y recuperación comprueban la revisión de reglas para impedir que una pantalla antigua sobrescriba cambios posteriores.

La captura es temporal y se cancela al detener/cambiar fuente. El perfil aplicado, su fecha/origen y las versiones previas se guardan en SQLite local, junto con las reglas. No se crean tablas ni se aumentan escrituras cloud. El cambio no modifica firmware, APK, Firebase, planes ni secretos.

## Verificación de implementación

- 131 pruebas Python correctas, incluidas siete nuevas para captura, permisos, aislamiento de simulaciones, datos vencidos, mediana, aplicación explícita, restauración versionada y almacenamiento por aula.
- npm run build correcto. Detector mecánico Impeccable: sin hallazgos. Revisión visual en el panel ejecutado.
- Receptor local reconstruido y actualizado; respaldo previo en artifacts/mq-calibration-backup. La distribución pública/ZIP portable y Hosting no se publican como parte de este cambio.

Una captura física representativa del ambiente y la clasificación de los picos 270–315 siguen siendo pasos de validación del sensor. Las pruebas con tiempo controlado verifican el software y no acreditan una calibración ambiental.

## Aplicación local verificada

Se guardó desde la sesión administradora la referencia de 85 ADC como provisional, con conditioned=false. La API confirmó el valor y la interfaz mostró la fecha del ajuste y una versión anterior recuperable. No se inició una captura física ni se confirmó acondicionamiento en nombre del usuario.

Revisión de adaptación: 390 px sin desbordamientos en controles; 1280 px con tres columnas para los rangos y referencia activa. La captura física sigue dependiendo de que el operador prepare el sensor y el ambiente. La prueba automática verificó la mediana con entradas controladas, no con datos ambientales certificados.

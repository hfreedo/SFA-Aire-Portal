# SFA Aire — firmware temporal para UNO sin sensores

Archivo: SFA_Aire_Simulador_USB/SFA_Aire_Simulador_USB.ino

## Cargar y probar

1. Conecta el UNO por USB. No se necesita MQ135 ni DHT. Si la PC está leyendo el puerto, pulsa Detener lectura antes de cargar.
2. Abre el archivo .ino en Arduino IDE. Selecciona Arduino UNO y su puerto USB/COM; pulsa Subir. No requiere instalar bibliotecas.
3. Abre Panel SFA Aire de esta carpeta de proyecto, inicia sesión y entra en Conexión Arduino. Selecciona el puerto y pulsa Conectar Arduino. El receptor local ya debe ser la versión actualizada para este ensayo.
4. Abre Mis aulas. La tarjeta debe indicar SIMULACIÓN · USB y mostrar una muestra reciente cada dos segundos. La temperatura varía entre 23,0 y 23,9 °C y la humedad entre 50 y 54 %.

MQ135 simulado:

| Tiempo desde MONITOR | Señal ficticia |
| --- | --- |
| 0:00 | 300 ADC |
| 1:00 | 400 ADC |
| 2:00 | 500 ADC |
| 3:00 | 600 ADC |
| 4:00 | 700 ADC |
| 5:00 | 300 ADC; comienza otro ciclo |

La subida es un escalón de 100 ADC por minuto, no una medición ni una conversión a ppm. El estado de prueba se calcula respecto a 300 ADC con persistencia de 12 s y recuperación de 20 s; un cambio de número no cambia inmediatamente el estado.

## Alcance de esta prueba

Los datos ficticios viajan del UNO a la PC por USB. Por defecto se muestran en una vista local en memoria. Para probar la app y los avisos, inicia sesión como administrador y, en Conexión Arduino, pulsa **Probar en la app y enviar avisos · 3 min**. Se autoriza el ensayo en Supabase, se reinicia el ciclo desde 300 y las muestras se guardan como SIMULACIÓN. Se reutilizan el motor de reglas, los incidentes y Firebase/FCM existentes.

El ensayo dura 180 s. Se conserva como máximo una muestra cada 3 s (con este firmware cada 4 s), dentro de la reserva de 61 muestras. Las primeras variaciones serán aproximadamente a 1:12 y la alerta a 2:12 desde el reinicio de secuencia, más el tiempo de transmisión. Los teléfonos deben estar registrados en esta misma aula y aceptar simulaciones. Al finalizar vuelve la vista local sin cerrar USB. No necesitas volver a cargar el firmware.

La app conserva su frecuencia de consulta actual: puedes pulsar Actualizar para ver la última muestra antes del siguiente ciclo automático. Una notificación push y una actualización del panel son verificaciones diferentes.

No cargar este simulador junto con un receptor antiguo: el diálogo de compatibilidad v2 impide iniciar la transmisión automática en esas versiones. La distribución pública previa aún no incluye esta mejora; usa el ejecutable local actualizado del proyecto.

## Comandos avanzados

115200 baudios, final de línea Nueva línea. Cierra el receptor antes de usar el monitor serie del IDE.

- SIMULACION_USB_V2: confirma compatibilidad para una prueba manual en el monitor serie.
- MONITOR: inicia muestras cada 2 s; los MONITOR repetidos no reinician el ciclo activo.
- PARAR: detiene. El siguiente MONITOR comienza desde 300 ADC.
- LEER: emite una muestra puntual; requiere compatibilidad confirmada.
- REINICIAR: vuelve a 300 ADC sin reiniciar la placa.
- ESTADO / AYUDA: diagnóstico e instrucciones.

## Volver a sensores reales

Detén la lectura y carga arduino/SFA_Aire_Aulas/SFA_Aire_Aulas.ino, que se conserva por separado con DHT11 en D2 y MQ135 AO en A0. Cambia DHT_TYPE si tu sensor real es DHT22. Después vuelve a conectar desde el panel.

## Validación

Compilado para arduino:avr:uno: 4816 bytes flash y 304 bytes RAM. Protocolo v1 del firmware real conservado; v2 agrega serial_contract=2 y simulated=true. Prueba física de este firmware pendiente hasta que Windows detecte la placa.

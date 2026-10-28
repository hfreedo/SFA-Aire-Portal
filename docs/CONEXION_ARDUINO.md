# Conectar la maqueta a un aula

En el portal de esta PC (http://127.0.0.1:8767/remoto):

1. Inicie sesión como administrador y seleccione el aula, por ejemplo Sala 3ro. BTI.
2. Abra **Conexión Arduino**. Si esta PC tiene otra aula, pulse **Usar esta PC para esta aula**.
3. Conecte el Arduino por USB, pulse **Refrescar puertos**, seleccione su puerto y **Conectar Arduino**.

La pantalla confirma el aula antes de habilitar el USB. No se descargan ni se copian credenciales. La PC recibe a 115200 baudios y envía MONITOR; Detener lectura envía PARAR. Cierre el monitor serie del IDE antes de conectar. Solo se propone automáticamente un único puerto identificado como USB/Arduino; los Bluetooth no se seleccionan automáticamente.

El recorrido es: DHT/MQ135 → Arduino → USB de esta PC → Supabase → emisor cloud FCM → teléfonos autorizados y registrados para el aula. El Arduino UNO necesita que esta PC permanezca encendida y conectada. El firmware conserva DHT D2 y MQ135 AO A0. MQ135 entrega una señal ADC relativa, sin inferir CO₂, AQI o ppm.

## Cambiar de aula y permisos

Debe administrar el aula actual y el destino. Se exige detener la lectura/prueba y sincronizar los paquetes pendientes antes del cambio. La asignación se realiza desde localhost, reutiliza una PC nunca utilizada del destino o crea una dentro del máximo de dos PC por aula. No toma registros con actividad ni revoca otras instalaciones. Conserva incidentes, mediciones e historial; los incidentes antiguos siguen asociados a su origen y no se reenvían al destino. Se conservan las guardas de consumo Free/Spark.

La configuración limitada se guarda automáticamente en secrets/supabase-pc.json y secrets/pc-bindings/. Nunca se devuelve al navegador ni se guarda la sesión del administrador. Los reintentos reutilizan el secreto pendiente para no duplicar PC tras una respuesta perdida.

## Verificación de esta entrega

Se comprobó la asignación real de esta instalación a Sala 3ro. BTI mediante la sesión administradora del portal y la consulta de la nube. La instalación independiente del Escritorio mantuvo su estado. Se detectaron únicamente COM5 y COM8 Bluetooth: no se abrió ninguno ni se afirmó una lectura física. La conexión USB y las mediciones reales quedan pendientes de conectar la placa.

Validación: 96 pruebas Python; 15 comprobaciones SQL locales; compilación web; recorrido visual a 1440, 390 y 320 px con puerto serie simulado. Este cambio no modifica firmware ni APK, ni representa una nueva prueba de entrega FCM.

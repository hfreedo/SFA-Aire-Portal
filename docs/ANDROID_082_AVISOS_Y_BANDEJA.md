# Android 0.8.2 · Avisos claros y bandeja personal

Actualización de la app Android; conserva el estilo IoT calmado de 0.8.1.

## Comportamiento

- La notificación identifica Alerta simulada / Aviso simulado o alerta / aviso real.
  El emisor cloud incorpora aula y valores disponibles. Una entrega antigua ya
  publicada en Android conserva su texto anterior.
- Avisos replegados: origen, estado, fecha y resumen temperatura/MQ135. Detalles y
  acciones despliega lectura fechada, humedad, nota, atención, compartir y entregas.
  El enlace de una notificación coloca su incidente primero y lo despliega.
- Pendientes y Atendidos se basan en el estado compartido del incidente. Archivo es
  organización personal EN ESTE TELÉFONO, por cuenta. Archivar no atiende, resuelve
  ni elimina el incidente, no cancela otros envíos y no afecta a otras personas.
  Restaurar devuelve el aviso a su categoría según el estado compartido vigente.
- El archivo permanece al actualizar la APK sobre la anterior y entre accesos de
  la misma cuenta. No se sincroniza entre teléfonos; borrar datos/desinstalar lo
  elimina. Máximo local: 500 identificadores. No almacena contraseñas ni tokens.
- Se organizan los avisos recientes que entrega el portal (hasta 30). No se añadió
  una descarga ilimitada de historia ni nuevas consultas periódicas.
- Mi aula usa tarjetas de sensor más compactas: iconos 24 dp, valores 28 sp, menor
  relleno. Mantiene texto de apoyo de 14 sp, vigencia visible y controles ≥48 dp.
- Con letra ampliada, las pestañas se recorren horizontalmente para conservar los
  nombres completos. No se reduce la fuente para hacerlas caber.
- Despliegue de detalles usa la animación existente y respeta Eliminar animaciones.

## Lectura del aviso y nube

La migración notice_reading_evidence añade trigger_observation/trigger_sample_at.
El disparador conserva sólo temperatura, humedad, MQ135 ADC, validez DHT y tipo de
prueba del paquete que crea o eleva el aviso, dentro de la MISMA transacción.
No busca la lectura actual ni aproxima datos de incidentes antiguos. Cambiar una
nota/atender no sustituye esa lectura. La elevación aviso → alerta puede capturar
el paquete de esa elevación, con su fecha visible.

Se conservan RLS, permisos RPC, guardas de consumo y el contrato FCM 2; los nuevos
campos de datos son opcionales. No se convierte MQ135 en CO2, AQI ni ppm. DHT
inválido o valores ausentes aparecen como No disponible. Los avisos antiguos sin
evidencia no se rellenan con una medición ajena.

El emisor aire-push se actualizó sin modificar sus secretos ni cron, planes,
Billing, cuotas o destinatarios. El cuerpo de la notificación es una lectura
histórica del aviso; no un indicador del estado ambiental actual.

## Verificación

Ver Entregas/VALIDACION_ANDROID_082.json y artifacts/android-082 para pruebas y
capturas nativas. Compilar/emular y usar transportes ficticios no demuestra
recepción FCM en el Samsung A02 ni funcionamiento físico de sensores. Ambas
verificaciones permanecen separadas y pendientes para esta APK.

## Diagnóstico del laboratorio web

Se corrigió en el código y build local AdminLab: hora visible de diagnóstico,
revisión de vigencia cada 5 s sin red, renovación al recuperar foco o seleccionar
PC (máximo una petición por 10 s para esos eventos), consultas sin solaparse y
reinicio del estado al cambiar de aula. Conserva sondeo de 60 s en reposo y 10 s
con prueba activa. No autoriza ensayos fuera de la RPC ni envía automáticamente.
El portable Windows publicado 0.8.0 no fue reemplazado/reempaquetado por esta tarea.
La prueba visual web aislada no generó mediciones ni notificaciones cloud.

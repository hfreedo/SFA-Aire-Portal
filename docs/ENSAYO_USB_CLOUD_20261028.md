# Ensayo UNO USB → Supabase → Android → avisos

Implementación local y RPC aplicados el 28/10/2026. El firmware alternativo existente no cambia: genera JSON v2 con simulated=true cada dos segundos y sube MQ135 cien ADC por minuto.

## Uso

1. Mantén el UNO conectado y leyendo en Conexión Arduino. Ingresa con la cuenta administradora del aula.
2. Pulsa **Probar en la app y enviar avisos · 3 min**. La PC solicita autorización a aire_lab_start_usb con la sesión del administrador. Las guardas existentes comprueban permisos, teléfono registrado para esa aula, aceptación de simulaciones, emisor y presupuestos.
3. La PC recibe el comando autorizado, conserva el USB, envía REINICIAR al firmware y procesa sus tramas reales de transporte. No genera valores en la PC para sustituirlos.
4. Las muestras se registran como SIMULACIÓN en SQLite y Supabase. Pasan por el mismo motor de reglas, creación/escalamiento de incidentes, cola durable, worker cloud y FCM. El consentimiento para simulaciones del teléfono sigue siendo obligatorio.
5. En Android selecciona la misma aula. La APK existente lee las muestras e incidentes sin cambios de contrato; conserva su frecuencia de consulta actual y permite actualizar manualmente. Recepción push y actualización visual son verificaciones diferentes.
6. Tras 180 s, o con Finalizar ensayo, vuelve la vista previa local y USB permanece abierto. Los incidentes existentes no se cierran automáticamente.

Desde el reinicio: 300 ADC al comenzar, 400 al minuto, 500 a los dos minutos. Referencia experimental de prueba 300; aviso tras 12 s de persistencia y alerta tras otros 12 s al cruzar el umbral correspondiente. Hay que sumar el ciclo de sincronización y la entrega FCM. No se garantiza recepción en un plazo fijo.

## Límites y compatibilidad

- Modo input_source=usb guardado en aire_lab_runs; las pruebas anteriores mantienen generated.
- Nuevo RPC de arranque autenticado, reservado a administradores por comprobación SQL. Anónimo no tiene EXECUTE. Reutiliza aire_lab_start y sus reservas: máximo 180 s, 12 ensayos/día, 3000 muestras/día, reserva independiente de push de laboratorio y guardas de almacenamiento/transferencia.
- Ingestión del ensayo USB no más de una vez cada 3 s; con el firmware de 2 s se guarda cada 4 s, unas 45 muestras, dentro de la reserva de 61. El panel USB sigue mostrando cada muestra recibida.
- Sin ensayo autorizado, el firmware simulado sigue en vista local sin ingestión cloud. Un paquete simulado no se procesa como una lectura física.
- Al finalizar se limpian los motores de decisión de prueba, sin cambiar la calibración real. Una trama de firmware real termina el ensayo USB antes de la ingestión física.
- Mismo contrato de datos/push y misma APK 0.8.2. No se han publicado Hosting ni un release/ZIP portable nuevos. El ejecutable de esta carpeta está actualizado y respaldado en artifacts/usb-cloud-backup.

## Validación

- Compilación web correcta; componentes reales de inicio/finalización revisados con fixture sin nube ni FCM. Captura artifacts/usb-cloud-controls-qa-20261028.jpg.
- Python: pruebas de reglas, outbox y permisos, incluyendo ciclo USB de 180 s con tiempo controlado, expiración, retorno al modo local, rechazo sin firmware simulado y RPC autenticado.
- PGlite: 14 comprobaciones de autorización, idempotencia, plan gratuito, modo USB persistido, muestras consultables por aire_overview y entregas creadas; cancelación no crea nuevas entregas.
- 15 pruebas de evidencia de notificación: medición original, escalamiento, historial y acceso.
- Migración aplicada en SFA Aire - Aulas y verificada: columna presente, anon sin permiso de arranque, authenticated puede solicitar con rol comprobado. Organización Supabase Free; no se vinculó Billing.

## Ensayo real confirmado el 28/10/2026

Se inició desde el navegador con la sesión administradora del usuario y el UNO real conectado por COM7, usando el firmware temporal. El primer ensayo registró 45 muestras y un aviso recibido en Android; permitió detectar una condición que omitía el push al escalar un incidente de más de 60 s.

Se corrigió aire_ingest_v02 en la migración 20261029000913_fresh_escalation_delivery.sql para evaluar la fecha de la muestra actual al escalar. Los incidentes históricos y los reintentos siguen sin crear entregas duplicadas. La prueba de regresión falla antes de la corrección y pasa después; también pasaron las comprobaciones de reservas, independencia de atención, evidencia de medición y worker cloud.

Segundo ensayo, después de la corrección:

- 180 s; 45 mediciones guardadas en Supabase, con 300, 400 y 500 ADC.
- Aviso recibido por Android a las 21:12:23, hora de Paraguay.
- Alerta recibida por Android a las 21:13:22, hora de Paraguay.
- Ambas entregas aceptadas por FCM y confirmadas por la app, en un intento cada una, sin errores.
- El usuario confirmó en el chat que vio una notificación y que se mostraban el aula y las mediciones. No se atribuye confirmación humana individual a cada entrega.
- Fin automático; USB conectado, regreso a vista local y cola vacía. No se atendieron automáticamente los incidentes de prueba.
- Dos ensayos y tres entregas reales de simulación en total, dentro de 12 ensayos y 20 entregas de laboratorio por día.

Evidencia estructurada: artifacts/PRUEBA_USB_CLOUD_REAL_20261028.json. Trazas del receptor: artifacts/usb-cloud-live-test-20261028.json y artifacts/usb-cloud-escalation-real-20261028.json.

Esta evidencia acredita USB físico y FCM real con datos ficticios. No acredita sensores físicos MQ135/DHT, calibración ambiental, resiliencia prolongada ni recepción individual de todas las cuentas posibles. La columna opened_at permanece sin acuse en las entregas consultadas; la confirmación humana se registra separadamente.

Skill aplicada: Supabase (configuración local en .codex/plugins/cache/openai-curated-remote/supabase/1.0.0/skills/supabase/SKILL.md). Se revisaron changelog y documentación oficial de funciones. Los avisos de auditoría anteriores sobre RPC con SECURITY DEFINER y tablas privadas sin políticas directas siguen correspondiendo al diseño de acceso por RPC; este cambio no amplía sus permisos. La nueva función revoca PUBLIC/anon y verifica rol administrativo.

Captura de la traza final: artifacts/usb-cloud-final-trace-20261028.jpg. En la comprobación SQL posterior, la función interna aire_ingest_v02 conserva EXECUTE revocado tanto para anon como para authenticated.

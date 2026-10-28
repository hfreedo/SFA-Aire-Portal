# Contrato v1 de datos y estados

## Serie

115200 baudios, Nueva línea. Comandos insensibles a mayúsculas: LEER (una
muestra), MONITOR (cada 3 s), PARAR, ESTADO, AYUDA. Las respuestas informativas
comienzan por `#` y el receptor solo procesa las líneas que comienzan con `{`.
No se inicia monitor periódico por el solo hecho de encender Arduino.

```json
{"device_id":"aula-01","mq_raw":335,"temperature":25.1,"humidity":54.2,"dht_ok":true,"warmed_up":true}
```

En fallo DHT: `dht_ok:false`, `temperature:null`, `humidity:null`. El ADC continúa
registrándose. Si `dht_ok:true` faltan ambos valores, se rechaza la trama.
Rangos: ADC 0–1023, temperatura -40–80, humedad 0–100, sin NaN/infinito.
`warmed_up` solo representa el temporizador de arranque; el acondicionamiento
real se confirma aparte. La hora es de recepción de la PC, no de RTC Arduino.

## API

Excepto `/health`, `/` y recursos estáticos, las rutas funcionales requieren
`Authorization: Bearer CLAVE_PC`. Documentación interactiva FastAPI en `/docs`;
use Authorize para consultar rutas protegidas.

| Método / ruta | Entrada / respuesta |
| --- | --- |
| GET `/health` | Salud de proceso; no demuestra sensores ni FCM |
| GET `/api/state` | Fuente, datos, reglas, incidentes, dispositivos sin token y entregas |
| GET `/api/history` | Últimas 120 muestras |
| GET `/api/ports` | COM disponibles |
| POST `/api/serial/connect` | `{"port":"COM3"}`; solo COM enumerados |
| POST `/api/stop` | Detiene fuente y cierra COM |
| POST `/api/simulation` | `{"scenario":"alerta"}` |
| PUT `/api/rules` | Objeto completo Rules; persiste y reinicia ventanas |
| POST `/api/devices` | installation_id, token FCM, name, accept_simulations |
| DELETE `/api/devices/{id}` | Desvincula y cancela entregas no enviadas |
| POST `/api/deliveries/{id}/receipt` | installation_id, action: recibido o abierto |
| POST `/api/incidents/{id}/attention` | action: atender/resolver; note de 3–500 caracteres |
| WS `/ws` | Primer mensaje `{"token":"CLAVE_PC"}` antes de 5 s; estado cada 2 s |

La app Android usa HTTP JSON nativo para no depender de una WebView. Consulta
cada 3 s cuando está visible; las notificaciones se reciben por FCM en su
servicio específico. React consulta estado/historia cada 2 s.

## Estados separados

Fuente: detenido / arduino / simulacion.

Observación: detenido / sin_datos / fallo_sensor / calentando / sin_calibrar /
normal / aviso / alerta. Normal significa ausencia de variación confirmada,
no certificación de aire saludable. Durante la confirmación se conserva el
último nivel; la señal y el gráfico permiten observar el cambio en curso.

Incidente: pendiente / en_atencion / resuelto. La recuperación ambiental no
resuelve automáticamente. Resolver exige estado normal reciente de la misma
fuente; cambiar a simulación no permite resolver un incidente de Arduino.

Entrega: pendiente / reintento / aceptado_fcm / recibido_app / error / vencido /
cancelado. `received` y `opened` se registran por entrega. No se almacenan
contraseñas Firebase en mensajes ni se publica el token de destino por GET.

Limitación: la clave compartida permite operar todo el prototipo. La asociación
installation_id limita el acuse accidental de otra instalación, pero no
reemplaza autenticación individual, roles ni atestación del teléfono.

## Extensión cloud v0.2

El contrato serie permanece sin cambios. La API local agrega
`GET /api/cloud/status` protegido por la misma clave. `/remoto` y `/remoto.html`
sirven el portal que autentica directamente con Supabase; no necesitan la clave
de PC. Con cloud configurado, `/api/incidents/{id}/attention` devuelve 409 e
indica atender desde el portal para evitar resoluciones divergentes.

RPC de usuarios autenticados: aire_overview, aire_history,
aire_create_classroom, aire_grant_member, aire_create_gateway, aire_attention,
aire_register_phone, aire_unregister_phone y aire_receipt. Las funciones de
gestión verifican rol y la consulta queda limitada por políticas RLS.

RPC del receptor: aire_gateway_status, aire_ingest, aire_claim_push y
aire_finish_push. Exigen secreto limitado de receptor y no una sesión docente.
Los paquetes contienen origin_id, seq, source, state, sample_at, observation e
incidents. El estado de atención de la nube es autoritativo. Consulte la
migración para tipos y parámetros exactos, y NUBE_V02 para configuración.

## Laboratorio y guardas v0.3

El protocolo serie sigue intacto. Se agregan a las observaciones `causes` y
`lab_run_id`. La calibración real no se modifica al simular. Rules agrega
temperature_enabled, temperature_warning, temperature_alert y
temperature_hysteresis; por defecto la regla térmica real sigue desactivada.
El plan experimental del laboratorio habilita esa regla temporalmente.

RPC admin: `aire_lab_panel`, `aire_lab_start` y `aire_lab_stop`. El receptor usa
`aire_gateway_poll` (estado, comandos y hasta 20 atenciones por sus IDs) y
`aire_lab_report`. Ingest solo admite simulaciones cloud con un ensayo
administrativo válido. Los alias internos v02 ya no son ejecutables por clientes.
Con cloud configurado, POST /api/simulation devuelve 403 para remitir al
laboratorio. El modo local independiente conserva su simulador de banco con la
clave del operador PC; no otorga acceso a roles cloud ni puede saltar sus RPC.

Las respuestas de cuota comienzan con CUOTA_. La PC conserva sus lecturas y
pausa reintentos cloud 15 min. El contador de JSON es una estimación de esta
app, no del egreso oficial. Ver LABORATORIO_Y_PLAN_GRATUITO.md para las guardas.

## Coordinación v0.4

Serie sin cambios. RPC autenticados adicionales:

- `aire_coord_panel(p_classroom_id)`: responsables, indicaciones, bitácora y entregas acotadas.
- `aire_set_duty(p_classroom_id,p_revision,p_coordinator,p_teacher,p_deputy)`: solo propietario del aula.
- `aire_take_coordination(p_incident_id,p_revision,p_note)`: coordinador o suplente designado.
- `aire_issue_instruction(p_incident_id,p_revision,p_id,p_action,p_reason,p_minutes)`: coordinador vigente; UUID estable y vigencia 1–120 min.
- `aire_respond_instruction(p_id,p_revision,p_action,p_note)`: destinatario; confirmada/aclaracion/impedimento/parcial/realizada.

`aire_attention` conserva firma y ahora aplica responsabilidades operativas;
resolver requiere coordinador vigente. Clientes anteriores pueden recibir
rechazo hasta asignar esos responsables. Creación de aulas requiere habilitación
SQL institucional y las membresías se conceden por el propietario.

Claim FCM agrega `event_id`/`event_kind` manteniendo id/lease/source/severity.
Una indicación reemplazada o vencida no admite nuevos acuses humanos. El estado
`notification_state` de la bitácora distingue encolado, falta de teléfono y cupo
agotado; encolado no significa aceptado por FCM ni recibido por el celular.
Ver `COORDINACION_V04.md` y la migración 003 para activación y contratos exactos.

## Reservas v0.5

Migración 004, sin cambios de firmas ni comandos. Budget agrega
`operational_push_today/limit`, `laboratory_push_today/limit` y
`operational_push_omitted_today` / `laboratory_push_omitted_today`.
Ingest devuelve `budget` junto con `accepted_seq`/`incidents`; el puente actualiza
el presupuesto sin entrar en pausa por agotamiento del cupo push.
Incidentes agregan `push_omitted_operational` y `push_omitted_laboratory`.
Eventos usan `cupo_operativo_agotado`, `cupo_laboratorio_agotado` o
`parcial_por_cupo` cuando corresponde. El agotamiento de otras guardas conserva
sus errores CUOTA_ y la pausa preventiva existente. Ver guía v0.5.


## Atención v2 preparada en desarrollo — 26/10/2026

No cambia el protocolo Arduino. Estado PC y overview cloud añaden
attention_contract=2. POST /api/incidents/{id}/attention conserva las acciones
atender/resolver; note es opcional (vacía por defecto, máximo 500 caracteres).
Resolver cierra la atención humana incluso sin lecturas normales, sin alterar
sensores, fuentes o snapshots.

aire_attention conserva nombre y parámetros. Note puede ser NULL/vacía; docente
o admin del aula no necesita turno, coordinador ni instrucciones completadas.
Se verifica identidad, aula y revisión; cierre registra closure_kind=atendido,
closed_by/closed_at/closure_reason y nota explícita para lectores antiguos.
La respuesta perdida de un mismo cierre puede reintentarse sin duplicar registro.
El resto de acciones y sesiones conserva sus protecciones anteriores.

Aplicar junto con la migración de ciclo de receptores y clientes nuevos.
La APK histórica conserva comportamiento anterior hasta actualizarse.
Compartir aviso es una función del cliente sin RPC ni efecto sobre la atención.

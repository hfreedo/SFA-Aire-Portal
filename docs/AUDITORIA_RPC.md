> Criterio actualizado por el usuario el 26/10/2026: se elimina la coordinación
> obligatoria. El flujo vigente de desarrollo es **Avisos → Marcar atendido**,
> nota opcional y comunicación opcional por el canal elegido. Las restricciones
> operativas de cierre propuestas anteriormente quedan reemplazadas por
> [ATENCION_SIMPLE](ATENCION_SIMPLE.md); se mantienen permisos y seguridad.
> Atención y capacidades ya activadas en Supabase el 26/10/2026.
> La APK distribuida y la actualización del contrato push siguen pendientes.

# Revisión RPC y ciclo de vida del teléfono

Estado: catálogo desplegado revisado en lectura; correcciones implementadas y probadas
localmente. Las dos migraciones de desarrollo todavía no están aplicadas en Supabase.

## Contraste con el despliegue

Se consultaron exclusivamente pg_proc, pg_policies y los asesores de seguridad del
proyecto SFA Aire - Aulas. No se ejecutaron RPC de negocio ni consultas a tokens,
usuarios, incidentes o secretos. El proyecto hermano no se modificó.

`herramientas/sql-check/audit-rpc.mjs` reconstruye las seis migraciones históricas en
PostgreSQL local con dobles de Vault/red/cron. Compara inventario, definición normalizada
por espacios y permisos anon/authenticated/service_role de las 45 funciones públicas
aire_* y privadas del worker, incluido dispatch_push: sin diferencias detectadas.
Esto enlaza las pruebas locales con el código desplegado; no prueba Auth/FCM reales.

Evidencias privadas de trabajo: `artifacts/cloud-all-functions-audit.json` y
`artifacts/cloud-rpc-drift-report.json`. No contienen valores de credenciales.

## Fronteras revisadas

| RPC | Condición efectiva en servidor | Alcance / control principal |
| --- | --- | --- |
| aire_role | auth.uid de la propia sesión | Rol de esa cuenta en el aula solicitada |
| aire_create_classroom | Habilitación en aire_creators | Máximo preventivo de tres aulas |
| aire_grant_member | Propietario institucional del aula | Roles permitidos, dueño no degradable, máximo diez miembros, responsabilidad vigente |
| aire_create_gateway | Admin miembro del aula | Secreto limitado al receptor; falta gestionar revocación y cantidad desde producto |
| aire_overview | Sesión identificada | Solo aulas propias; incidentes 30, entregas 50, respuesta medida |
| aire_history | Miembro del aula | Fuente solicitada, máximo 60 lecturas, respuesta medida |
| aire_coord_panel | Miembro del aula | Aula propia, exposición acotada de correos y trazas, límites de respuesta |
| aire_set_duty | Propietario institucional | Revisión, miembros operativos, personas distintas e incidentes abiertos |
| aire_take_coordination | Coordinación o suplencia asignada | Aula, revisión e incidente vigente |
| aire_attention | Docente o coordinador operativo vigente | Membresía, revisión y estado; cierre por coordinador con lectura reciente y resultado completo |
| aire_issue_instruction | Coordinador vigente del incidente | Revisión, vigencia 1–120 min, UUID idempotente, receptor docente asignado |
| aire_respond_instruction | Destinatario de la indicación | Membresía, revisión, vigencia y comprensión antes del resultado |
| aire_register_phone | Miembro del aula | Registro propio; límite tres teléfonos; corrección de vínculos antiguos preparada |
| aire_unregister_phone | Sesión identificada | Solo filas/entregas de su user_id y registro |
| aire_receipt | Destinatario de la entrega | user_id, vínculo y membresía; rechazo explícito de acción NULL preparado |
| aire_lab_start | Admin del aula | Receptor reciente, confirmación Free/Spark, idempotencia, duración/intervalo, cupos de prueba/lecturas/push y tamaño |
| aire_lab_stop | Admin del aula de la prueba | Cancela prueba y entregas pendientes |
| aire_lab_panel | Admin del aula | Receptor/ensayos del aula y resultados acotados |
| aire_cloud_status | Admin del aula | Estado y cupos del emisor; sin devolver secretos |
| aire_ingest | Receptor habilitado + hash de secreto | Origen, secuencia, fuente, reloj, payload y ensayo autorizado; guardas globales |
| aire_gateway_poll | Receptor habilitado + hash de secreto | Incidentes del receptor, máximo veinte IDs; ensayo propio |
| aire_lab_report | Receptor habilitado + hash de secreto | Solo su ejecución de laboratorio y estados permitidos |
| aire_claim_push | Receptor habilitado + hash de secreto | Separación cloud/PC, lease, destinatario/membresía/consentimiento y vigencia |
| aire_finish_push | Receptor habilitado + hash de secreto | Entrega de su receptor y lease; validación de resultado ambiguo preparada |

Las cinco funciones aire_cloud_configure/open/health/claim/finish son exclusivas de
service_role. Open valida credencial de worker y cupos; claim revisa membresía, teléfono,
consentimiento, vigencia y lease; finish exige lease coincidente de reclamación. Dispatch usa
Vault, cooldown, separación de transporte y máximo 600 despachos diarios / 10 000 mensuales.
Los helpers y versiones internas no conceden ejecución directa a roles de aplicación.
Los permisos no derivan de user_metadata ni de ocultar botones.

Las políticas SELECT consultadas restringen cada fila por aire_role(aula). Las tablas
sin políticas se mantienen cerradas para acceso directo y se operan mediante RPC.
Los avisos del asesor sobre SECURITY DEFINER siguen presentes por este diseño: se
revisaron sus entradas y helpers; no se hicieron grants generales para silenciarlos.
Referencia del asesor: https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable

## Hallazgos corregidos en desarrollo

1. Un registro opaco nuevo por sesión podía acumular teléfonos tras salida offline y
   agotar tres cupos. Ahora `device_id` estable se separa del vínculo `installation_id`.
   `aire_register_phone_v2` recibe UUID de dispositivo y vínculo, conservando el RPC v1.
   El núcleo privado comprueba membresía/entradas antes de retirar registros antiguos.
2. Cambiar de cuenta o rotar token podía conservar destinatarios antiguos del mismo
   teléfono. El registro retira las coincidencias de dispositivo o token con otro
   usuario/vínculo, cancela sus entregas pendientes y libera leases. Conserva otras
   aulas de la misma sesión y actualiza allí el token, sin copiar consentimientos.
3. Una cuota fallida debe revertir también esa limpieza. Todo ocurre dentro de la misma
   transacción y bloqueo global; la regresión verifica que el registro anterior permanece.
4. Un acuse con acción NULL podía marcar recepción sin expresar una acción válida.
   Se rechaza antes del UPDATE y se comprueba que received_at permanece NULL.
5. El resultado PC admitía proveedor/error ambiguos. Un validador privado compartido con
   cloud exige exactamente proveedor o error no vacío y conserva los controles de lease.

Migración: `supabase/migrations/20261025200720_harden_phone_lifecycle.sql`.
Android llama al nuevo RPC con el dispositivo estable y vínculo de la sesión capturada.
Los identificadores son correlación; la autorización sigue dependiendo de Auth/RPC.
El cliente no puede consultar tokens ajenos. Un token FCM debe tratarse como dato privado:
su posesión permite correlacionar la sustitución del canal, sin otorgar acceso a las aulas.

## Verificación y límites

- 45 comprobaciones nuevas en `phone-lifecycle.test.mjs`: cambio de cuenta, sesión/token,
  reinstalación, varias aulas, límite de tres teléfonos, rollback, aislamiento de aula,
  entradas NULL, cliente v1, propiedad del acuse, resultado PC/cloud y grants de helpers.
- 42 comprobaciones cloud SQL existentes, 132 base y 48 pruebas Python correctas.
- Compilación Android y 32 pruebas JVM correctas. El registro v2 aún no se ejercitó contra
  Supabase alojado; la instrumentación previa de notificaciones no acredita ese RPC nuevo.
- Sin envíos FCM reales, cambios de Billing, migraciones remotas ni sustitución de la APK
  histórica. Los dobles de Vault/red/cron no acreditan esos servicios alojados.

## Pendientes que esta revisión deja concretos

| Prioridad | Trabajo | Impacto |
| --- | --- | --- |
| Alta | Gestión de receptores: límite, revocación/sustitución y cancelación de trabajo | Permitir retirar credenciales y evitar generación acumulativa |
| Media | Capacidades institucionales en Administración web | El servidor restringe propietario/creador, pero algunos formularios siguen habilitados para cualquier admin |
| Verificado en desarrollo | Entrada Android separada | Launcher limpio; pantallas internas no exportadas, rechazo desde UID externo y PendingIntent propio probados. Detalle en AUDITORIA_ARQUITECTURA. |
| Alta | Activar ambas migraciones y emisor, después APK y prueba real con dos cuentas | Cerrar evidencia de sesión, privacidad y entrega real |
| Media | Consolidar tokens/estilos y preparar entrega versionada | Unificar composición y garantizar que el artefacto contiene lo auditado |


## Activación de atención sencilla — 26/10/2026

Migraciones gateway_lifecycle_capabilities y simplify_alert_attention aplicadas.
El overview autenticado devuelve attention_contract=2 y can_resolve=true para
los cuatro avisos de la cuenta admin. Cierre con nota vacía comprobado con rol
authenticated dentro de una transacción revertida. Permanecen cuatro pendientes
y cero registros de atención; el usuario conserva su decisión sobre el cierre.
Sin UPDATE directo, ejecución anónima ni helper privado accesible al cliente.

Asesores posteriores: las once tablas sin políticas siguen restringidas a RPC;
cinco avisos anon definer son los receptores con credencial propia. Los 27 avisos
authenticated definer incluyen tres RPC nuevos con autorización interna. No se
abrieron tablas para eliminarlos. Referencias del proveedor:
[funciones SECURITY DEFINER autenticadas](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable),
[tablas RLS sin políticas](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).
El aviso previo de protección de contraseñas filtradas se mantiene, sin contratar
planes ni cambiar Billing; [referencia](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

La activación no incluye las migraciones push/sesión pendientes ni cambios del
emisor Firebase. Evidencia en artifacts/cloud-attention-activation.json.

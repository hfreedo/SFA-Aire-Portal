> Criterio actualizado por el usuario el 26/10/2026: se elimina la coordinación
> obligatoria. El flujo vigente de desarrollo es **Avisos → Marcar atendido**,
> nota opcional y comunicación opcional por el canal elegido. Las restricciones
> operativas de cierre propuestas anteriormente quedan reemplazadas por
> [ATENCION_SIMPLE](ATENCION_SIMPLE.md); se mantienen permisos y seguridad.
> Atención y capacidades ya activadas en Supabase el 26/10/2026.
> La APK distribuida y la actualización del contrato push siguen pendientes.

# Auditoría de arquitectura y seguridad — en curso

Objetivo: unificar responsabilidades, navegación y seguridad de web, Android y receptor,
con contratos explícitos y evidencia por recorrido. Esta auditoría no se declara terminada
por completar compilaciones o una revisión de diseño.

## Estructura de destino

| Capa | Responsabilidad | No debe hacer |
| --- | --- | --- |
| Dominio | Estados, caducidad, roles de presentación, transiciones y límites | Red, almacenamiento, componentes visuales |
| Datos e infraestructura | Transporte, sesión, persistencia, RPC y adquisición USB | Decidir la composición de pantallas |
| Aplicación | Casos de uso: iniciar sesión, consultar aula, atender, coordinar, probar | Duplicar permisos del servidor como autorización efectiva |
| Presentación | Navegación única, formularios, jerarquía visual y estados de error | Leer tokens o construir reglas de negocio dispersas |
| Plataforma cloud | RLS/RPC por actor/aula, outbox, consumo y FCM | Aceptar permisos solo porque un botón esté oculto |

La unificación mantiene dos transportes explícitos (LAN y cloud), identificados desde el
panel y Ajustes. Un único transporte implícito confundiría sus garantías de acceso y acuse.
No se sustituye la autorización en servidor por una validación local.

## Hallazgos y estado

| ID | Prioridad / impacto | Evidencia inicial | Implementación / pendiente |
| --- | --- | --- | --- |
| SEC-01 | Alta: credenciales en transporte | Api local seguía redirecciones; CloudApi usaba otra política | EndpointPolicy y JsonTransport compartidos: sin redirecciones, HTTP solo privado literal, URL base sin usuario/ruta/query, límite de respuesta y secreto rechazado en la frontera de transporte. Pruebas de regresión JVM. |
| SEC-02 | Alta: tokens en disco | cloud_access/cloud_refresh en SharedPreferences | Repositorio de sesión con AES-GCM y clave Android Keystore; migración del mismo archivo sin mantener campos anteriores; prueba instrumentada aislada aprobada en emulador API30. |
| SEC-03 | Alta: sesión renovada tras salir | Respuesta de refresh podía guardar otra vez tokens después de logout | Generación local de sesión; escritura tardía rechazada. RequestScope descarta callbacks de contextos abandonados; WorkspaceResult vincula datos a su generación y CareCommands se ejecuta con la generación de la vista verificada. Pendiente ensayo de dos cuentas reales. |
| SEC-04 | Alta: cambio de cuenta y notificaciones | Cola de acuses sin propietario/generación; mensajes tardíos podían mostrarse tras logout | Se bloquean avisos cloud sin sesión/ruta activa y se limpia cola cloud al salir. Los acuses nuevos incluyen generación y el transporte verifica esa generación; los heredados sin contexto se descartan. Vínculo push por generación y cola cloud2 implementados y verificados con sesiones ficticias en emulador, también para publicación/apertura tardías. Pendiente activar contrato v2 en nube y verificar dos identidades reales con FCM; no atribuir esa prueba a fixtures. |
| ARC-01 | Media/alta: controlador monolítico | RemoteWorkspace y CloudActivity mezclan sesión, red, casos de uso y renderizado | Web: acceso, monitoreo, incidentes e historial en pantallas por función y sidebar compartida con LAN. Dominio web y transporte/sesión Android separados. Android: pantallas de acceso/aula/incidentes/coordinación/ajustes, shell, componentes comunes, formularios y casos de uso extraídos. Sesión y administración web extraídas; LAN Android reutiliza componentes y formularios comunes, pero conserva controlador técnico propio. Pendiente consolidar estilos y terminar revisión cloud/identidades. |
| ARC-02 | Media: reglas visuales duplicadas | Etiquetas y caducidad repetidas | domain/monitoring.ts unifica presentación de estados, caducidad, filtros y habilitación de atención web; pruebas de fechas inválidas y límites. ObservationState.kt unifica etiqueta/caducidad Kotlin y trata fechas inválidas como vencidas; CarePolicy centraliza habilitación de respuestas y vigencia. |
| UX-01 | Media/alta: flujo de atención inconsistente | Prompts, notas perdidas, configuración técnica en acceso | Corregido en v0.6.2; regresión visual y funcional se repite tras refactor. |
| UX-02 | Media: CSS acumulativo y navegación | Overrides sucesivos y estilos por pantalla | Pendiente tokens de diseño, componentes de shell/formulario/estado y consolidación CSS; comparar capturas. |
| OPS-02 | Alta: integridad del código entregado | El patrón global data/ y el filtro de paquetes omitían los nuevos módulos Kotlin | Se distingue /data de ejecución del paquete Kotlin data. Pruebas incluyen cada fuente Kotlin de producción y conservan exclusión de secretos, builds y datos. |
| OPS-01 | Alta: trazabilidad de entregas | Fuente puede cambiar sin nueva APK distribuida | La entrega v0.6.2 se conserva. Cambios de esta auditoría son desarrollo hasta completar pruebas y preparar versión nueva; no sobrescribir el APK/ZIP histórico ni atribuirle estas mejoras. |
| SEC-06 | Alta: secreto LAN | La clave del receptor LAN seguía en preferencias privadas sin cifrado | LanConnectionRepository protege dirección y clave juntas con AES-GCM/Keystore, migra y elimina campos anteriores en una edición. Validación instrumental de migración, alteración y separación LAN/cloud. Cambio de desarrollo; APK distribuida aún anterior. HTTP privado sigue limitado a la maqueta. |
| SEC-05 | Alta: autorización y economía cloud | RPC y migraciones existentes | Revisión completa de grants/RLS/RPC, alcance de worker, leases, idempotencia y guardas aún pendiente; no crear servicios ni cambiar Free/Spark. |

## Pruebas y requisitos de aceptación

1. Red Android: rechazar claves privilegiadas en todos los accesos, URL inválida,
   redirecciones con Authorization y respuestas excesivas; conservar errores y tipos RPC.
2. Sesión Android: cifrado con Keystore, modificación detectada, migración sin texto
   plano residual, logout efectivo local y bloqueo de renovación tardía. Test instrumental
   con preferencias/alias exclusivos y datos ficticios; sin red ni cuenta del usuario.
3. Identidades: comprobar dos cuentas, tokens FCM rotados, cola de acuses, cambios de
   aula, logout offline y respuesta tardía. No sustituir esto con compilar.
4. Web: build y pruebas de recorridos/caducidad/permisos; escritorio/móvil sin regresión
   en acceso, aula, incidentes, coordinación y laboratorio.
5. Receptor: integración Python; conservar serial/API y exclusión de fuentes. No afirmar
   ejecución física ni FCM real con pruebas simuladas.
6. Cloud: pruebas SQL/RLS y worker con casos de acceso indebido, repetición y cupos;
   revisión de despliegue solo después de que el cambio local esté probado.
7. Arquitectura: los componentes de presentación no leen secretos; las reglas de dominio
   y las conexiones tienen una ubicación única; documentación y entrega coinciden.

Fuentes técnicas consultadas: Android Keystore
https://developer.android.com/privacy-and-security/keystore y API Base64 (API 26)
https://developer.android.com/reference/java/util/Base64 .

## Ubicaciones ya separadas

- `interfaz_web/src/domain/monitoring.ts`: reglas puras de presentación compartidas.
- `android_app/.../data/network/`: política de endpoints, transporte y decodificación RPC.
- `android_app/.../data/session/`: persistencia cifrada y generación de sesión.
- `android_app/.../data/notifications/`: formato de acuses con contexto de sesión, validación de identificadores y compatibilidad LAN explícita.
- `CloudApi` y `Api`: adaptadores cloud/LAN que usan las fronteras anteriores.
- `CloudActivity`: composición, ciclo de vida, permisos de plataforma y coordinación de navegación; los renderizadores y comandos se extraen a ui/application/domain.

La persistencia usa AES-GCM y Android Keystore; no se afirma que todos los dispositivos
ofrezcan almacenamiento de clave en hardware. El servidor sigue autorizando cada RPC.
Logout local no revoca por sí solo un JWT que ya está en circulación; la revisión del
cierre remoto y de la ruta de notificaciones sigue abierta en SEC-04/SEC-05.

## Guardas de acuses introducidas

Cola local limitada a 256 elementos, lotes de hasta 16 intentos, validación UUID/acción
antes del transporte y descarte de entradas inválidas que podrían bloquear el resto.
Alcanzar capacidad deja aviso visible en Ajustes; no se atribuye recepción humana.
Los acuses cloud heredados sin generación se descartan: no puede demostrarse su
asociación a la cuenta actual. El backend conserva la validación de destinatario.
Una generación separa sesiones locales; no sustituye la comprobación de actor/aula
ni identifica por sí sola al destinatario de un mensaje FCM recibido tarde.

## Verificación del avance actual

- Android: 29 pruebas JVM correctas; assembleDebug y APK instrumental compiladas.
- Emulador API30: prueba real de Android Keystore/migración/modificación/cierre y
  generación de acuses aprobada; arranque de Mi aula DEMO comprobado visualmente.
- Web: build, 4 pruebas de dominio y recorridos funcionales/visuales escritorio/móvil.
- Receptor: 43 pruebas Python correctas.
- PostgreSQL local: 132 comprobaciones base y 35 cloud; worker: 7 pruebas con
  transporte simulado. No verifican por sí solas el despliegue cloud ni FCM real.
- Informe legible por máquina: `Entregas/AUDITORIA_ARQUITECTURA_AVANCE.json`.
- La APK distribuida v0.6.2 conserva su SHA256 original; esta auditoría aún no es
  una actualización publicada ni una nueva recepción física demostrada en A02.

## Avance: pantallas web y distribución

- `features/access/LoginScreen.tsx`: formulario de acceso; no conoce cliente Supabase ni configuración técnica.
- `features/monitoring/ClassroomScreen.tsx`: lecturas y atención del aula.
- `features/incidents/IncidentsScreen.tsx`: listado, filtros y selección de atención.
- `features/history/HistoryScreen.tsx`: consulta y presentación del historial.
- `shared/layout/WorkspaceSidebar.tsx`: navegación y marca compartidas por cloud/LAN.
- `RemoteWorkspace.tsx`: composición, ámbito de aula y coordinación de acciones; aún requiere extraer sesión y casos de uso.

Las pantallas nuevas reciben datos y callbacks; no ejecutan RPC ni leen almacenes de
credenciales. La navegación restringida también se abandona si el rol del aula cambia.
La política de paquetes ahora incluye el código Kotlin del paquete `data` sin permitir
la carpeta de datos de ejecución. Una prueba enumera todas las fuentes Kotlin reales,
además de comprobar ejemplos de archivos que deben permanecer excluidos.

## Avance Android: responsabilidades separadas

- `ui/WorkspaceLayout.kt`: shell, identidad y navegación principal.
- `ui/AireUi.kt`: componentes, tipografía, colores, espacios y controles comunes.
- `ui/screens/`: AccessScreen, ClassroomScreen, IncidentsScreen, CoordinationScreen y SettingsScreen; reciben datos y callbacks, sin red ni almacenes de credenciales.
- `ui/CareDialogs.kt`: formularios, validación visual, estado de guardado y conservación de notas.
- `application/WorkspaceActions.kt`: autenticación, consulta, comandos, registro de teléfono y cierre.
- `application/CareCommands.kt`: contratos de atención, revisión del registro e identificador estable de indicación.
- `application/RequestScope.kt`: descarta resultados de una pantalla invalidada; no revierte operaciones ya aceptadas en servidor.
- `domain/ObservationState.kt`: caducidad y etiquetas; fecha inválida no interrumpe la pantalla.
- `domain/CarePolicy.kt`: decisiones de presentación por responsabilidad, vigencia y estado conocido.

El registro FCM no depende de una referencia antigua al checkbox de Ajustes. Captura
consentimiento y generación de sesión; el callback tardío se descarta si cambió el
contexto. Un tiempo de espera acotado permite reintentar sin congelar la navegación.
La autorización efectiva sigue siendo responsabilidad de los RPC.

La interacción nativa de formularios se prueba con callbacks controlados en el
emulador, sin ejecutar comandos cloud. El cierre de esta revisión depende del resultado
instrumental y de la revisión visual de las pantallas extraídas, no solo de compilación.

## Verificación cloud en modo de solo lectura

Se confirmó el proyecto `SFA Aire - Aulas` mediante el conector Supabase y se consultaron
advisors y catálogos PostgreSQL, sin llamar RPC de negocio, crear alarmas ni modificar
configuración. Es una revisión parcial del despliegue, no el cierre de SEC-05.

- Las 18 tablas inspeccionadas tienen RLS habilitado y ninguna permite escrituras
  directas de anon/authenticated. Solo classrooms/members permiten SELECT authenticated;
  sus políticas necesitan revisión junto con las funciones de ámbito.
- El aviso INFO de 11 tablas sin políticas se contrasta con sus grants: no se habilita
  acceso directo para eliminar el aviso. El acceso previsto es por RPC autorizado.
- Cinco funciones gateway tienen EXECUTE anon/authenticated como API de receptores,
  con `search_path` vacío. Se inspeccionaron wrappers y tres helpers de autenticación;
  el helper valida receptor habilitado y hash de credencial, y esos helpers no son
  ejecutables por anon/authenticated. Esto no reemplaza revisar todas las rutas.
- El asesor también marca 24 funciones SECURITY DEFINER accesibles a authenticated;
  cada una requiere justificar rol, aula, revisión y límites. No se revocan a ciegas.
- Leaked password protection está desactivada. La documentación oficial la limita a
  Pro o superior; se registra como restricción de Free, sin activar Billing ni cambiar plan.

Referencias de los avisos:
[RPC accesible a anon](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable),
[RPC accesible a authenticated](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable),
[RLS sin políticas](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy),
[seguridad de contraseñas y planes](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

Las definiciones de funciones y grants consultados se conservaron como evidencia de
lectura en artifacts/cloud-security-*.json. No contienen filas de cuentas ni secretos.

## Unificación de atención en Android

El modo LAN también utiliza AireUi y CareDialogs: validar no cierra el formulario,
un rechazo conserva la nota y un cambio de conexión invalida resultados pendientes.
El contenido cloud de coordinación se distribuye en metadatos legibles, indicación
separada y registro desplegable. Los controles operativos quedan bloqueados cuando
no hay una vista de sesión verificada; el backend conserva su propia autorización.

## Evidencia de interacción y presentación Android

La prueba instrumental de formularios usa ventanas Android reales y callbacks de
prueba: nota demasiado corta no guarda, rechazo conserva la nota, cancelar cierra,
vigencia inválida no emite e identificador de indicación se mantiene estable. Se
integra en SessionVaultInstrumentation y no llama RPC de negocio.

`herramientas/android_screens_audit.py` recorre Mi aula, Incidentes, Ajustes, salida
al acceso y modo LAN en el emulador propio. Captura XML y PNG, comprueba ausencia de
campos técnicos en el acceso y coherencia de fechas del ejemplo. La revisión visual
queda en `artifacts/android-screens-audit/`; no equivale a ejecución en A02 ni a FCM real.
Los fixtures se cargan desde `data/demo/DemoWorkspace.kt`, fuera de Activity, con
fechas explícitas y sin acciones de red.

## Avance web: sesión y administración

- `application/session/CloudSession.ts`: único ciclo de vida de identidad, restauración,
  acceso, cierre, preview y resultados RPC. Puede probarse sin React ni SDK.
- `data/cloud/sessionPort.ts`: adaptador del SDK instalado; captura identidad y bearer
  por solicitud, desuscribe eventos y libera el cliente al reemplazarlo.
- `data/cloud/client.ts`: validación pública, creación del SDK y nombre único del almacén.
- `domain/models.ts`: contratos de datos sin dependencia de red.
- `data/demo/overview.ts`: fixture separado; no inicia sesiones.
- `features/access/useInstitutionSession.ts`: conexión del ciclo de vida a React.
- `application/workspace/ResultScope.ts`: contexto de cuenta/aula/fuente/página para
  descartar resultados fuera de su ámbito, incluso al volver al mismo ámbito después.
- `application/workspace/ClassroomAdministration.ts`: casos de uso de aula/cuentas/receptor.
- `features/administration/AdministrationScreen.tsx`: estado local de los formularios
  y del vínculo descargable. La credencial desaparece al salir/cambiar ámbito; un
  resultado tardío no se muestra en otro ámbito. Solo se exportan los campos permitidos
  de un vínculo validado contra el aula solicitada y el contrato del receptor.

Se retiró `src/cloud.ts`: tipos, fixtures y SDK ya no comparten una implementación.
La configuración pública se toma del receptor actual, sin elegir una instalación a
partir de un caché público anterior. La sesión continúa en sessionStorage del proyecto.
Cerrar el navegador/local no invalida de inmediato un JWT que ya circula; la autorización
real se conserva en el servidor. En fallo de salida remota se retira caché local y se
informa la falta de confirmación, sin simular revocación global ni cerrar otros teléfonos.

### Regresiones de sesión y contexto

`herramientas/web-session.test.mjs`: 10 pruebas de restauración tardía, salida durante
login, cambio de cuenta con RPC pendiente, doble acceso, salida offline, fallo de
almacenamiento, preview sin SDK, descarte de resultados y contrato de administración.

`herramientas/sql-check/session-context-web.cjs`: usa el SDK instalado en navegador
contra endpoints interceptados. Comprueba cambio de aula/cuenta con historial pendiente,
vínculo pendiente tras cambio de aula, ocultación del vínculo actual, salida de gestión
al perder rol admin en el aula y descarte del caché de configuración obsoleto. No crea
cuentas reales ni ejecuta comandos en Supabase/Firebase.

La composición de administración agrupa aula/cuenta en dos columnas y el receptor en
un bloque separado; pasa a una columna en móvil. La revisión visual incluye la pantalla
de gestión en DEMO con creación y vínculo bloqueados.

El empaquetado permite ahora `interfaz_web/src/data` como código sin abrir carpetas de
datos de ejecución. Una prueba enumera todas las fuentes TS/TSX/CSS reales, además de
las fuentes Kotlin, y conserva las exclusiones de secretos y archivos privados.


### Validación de este avance

Compilación web correcta; 14 pruebas Node (4 de dominio y 10 de sesión/aplicación)
y 48 pruebas Python correctas. Los recorridos de atención, sesión/contexto y presentación
pasan en navegador con endpoints controlados. Se inspeccionaron las capturas de
administración de escritorio y móvil: sin desbordamiento horizontal ni errores JavaScript.
Estas comprobaciones no envían push real ni sustituyen la prueba de dos cuentas reales.

Se verificó que las fuentes Android registradas y el SHA-256 del APK distribuido 0.6.2
siguen idénticos. No se recompiló Android en esta etapa porque no hubo cambios en él.
El registro actualizado está en `Entregas/AUDITORIA_ARQUITECTURA_AVANCE.json`.

Continúan pendientes el alcance de mensajes FCM tardíos
al cambiar de cuenta, la revisión completa de autorización RPC y la consolidación de
estilos/tokens. Después corresponde validar dos cuentas y preparar una entrega versionada.


## Protección de conexión LAN Android

`data/session/KeystoreCipher.kt` concentra AES-GCM y Android Keystore; la sesión cloud
conserva alias, propósito y formato previos. `LanConnectionRepository.kt` usa su propio
alias y propósito, y cifra dirección y clave como una unidad. Api consume únicamente
ese repositorio; MainActivity ya no lee ni escribe secretos en preferencias directamente.
La migración retira `server`/`key` al confirmar el sobre cifrado en una única edición.

Un sobre alterado se rechaza sin recurrir al secreto heredado. El formulario muestra el
error y permite introducir de nuevo dirección y clave. Guardar una dirección inválida o
una clave con salto de línea conserva la conexión anterior y evita iniciar la operación.
Las preferencias de consentimiento y ruta push se mantienen separadas del secreto.

Prueba instrumental en emulador API30: ida/vuelta cifrada, ausencia de clave visible,
migración, sustitución completa de PC/clave, rechazo de HTTP público e inyección de
cabecera, alteración detectada, recuperación y separación del propósito LAN/cloud.
También repitió las comprobaciones de sesión cloud y formularios nativos existentes.
Evidencia: `artifacts/auditoria-keystore-lan.txt`. No hizo RPC ni envió push real.
`assembleDebug`, `assembleDebugAndroidTest`, 29 pruebas JVM y 48 Python correctos.
Esto no acredita instalación en A02 ni una nueva entrega distribuida.

Para esta ejecución Gradle necesitó `JAVA_TOOL_OPTIONS=-Djdk.net.unixdomain.tmpdir=C:/Users/Public`
por un fallo de conexión Unix-domain del JBR con el temporal abreviado de Windows.
Se aplicó al proceso de compilación, sin modificar variables globales ni reglas de red.


## Notificaciones y cambio de identidad

`NotificationPolicy.kt` concentra el contrato de entrada y el vínculo de registro;
`SessionRepository` entrega un contexto generación/vínculo y serializa la publicación
con el cierre local. El identificador derivado con UUID es un identificador de correlación,
no un secreto ni prueba de autorización. Los RPC siguen comprobando cuenta, aula y registro.
`AireMessagingService` aplica esa política antes del acuse, respeta la ruta elegida y
usa PendingIntent con URI propia por entrega/vínculo. `CloudActivity` valida el contexto
al tocar un aviso antes de cambiar aula o encolar apertura. La cola anterior sin contrato
v2 se descarta; la cola LAN continúa siendo independiente.

Ajustes diferencia permiso del sistema de registro confirmado para sesión/aula. Tras
actualizar desde una versión anterior o entrar con otra cuenta, muestra registro pendiente
hasta que el RPC confirma el nuevo vínculo. Esto no confirma recepción de un push.

La migración `20261025195629_bind_push_to_session.sql` añade `installation_id` a los
trabajos reclamados mediante envoltorios; conserva cuerpos previos, permisos, leases,
orden, máximos y validación de receptor. Los cuerpos anteriores y el auxiliar quedan
sin ejecución directa para anon/authenticated/service_role. Worker y emisor Python
incluyen contrato v2, sin exponer user_id. Todavía no se desplegó esta migración/emisor.
El orden y las restricciones de actualización están en ARQUITECTURA.

Validación local: 42 comprobaciones cloud SQL (incluido acuse por otra cuenta/registro y
reclamación PC con vínculo), 132 comprobaciones base SQL, 8 pruebas del worker con FCM
simulado, 48 Python, 32 JVM, assembleDebug y assembleDebugAndroidTest. Instrumentación
API30 con preferencias/alias ficticios demuestra estabilidad tras recrear repositorio,
rotación tras salida, rechazo de mensaje anterior en la misma aula y bloqueo de la acción
de publicación/apertura y encolado de su acuse después del cambio de sesión. No llama
RPC ni usa identidades cloud reales. Evidencia: `artifacts/auditoria-notification-binding.txt`.

La captura `artifacts/notification-settings.png` corresponde al componente nativo Ajustes
con estado ficticio de registro pendiente; el aviso fue comprobado por accesibilidad y
revisión visual. Fuentes técnicas de contraste: mensajes de datos FCM
https://firebase.google.com/docs/cloud-messaging/customize-messages/set-message-type
 y migraciones https://supabase.com/docs/reference/cli/supabase-migration-new .
No se enviaron pushes reales ni se modificaron Billing o la APK histórica distribuida.


## Contraste RPC desplegado y corrección del registro

Revisión detallada: [AUDITORIA_RPC.md](AUDITORIA_RPC.md). El catálogo desplegado se
contrastó con seis migraciones históricas: 45 definiciones/permisos coinciden tras
normalizar espacios; no hubo RPC de negocio en nube. Se revisaron las 24 entradas
expuestas a authenticated (19 de cuentas y 5 de receptores), cinco de service_role,
helpers y políticas SELECT. Los asesores no se silenciaron con permisos nuevos.

El contraste identificó acumulación de teléfonos al rotar vínculo con logout offline,
acuse NULL y resultados ambiguos del transporte PC. `20261025200720_harden_phone_lifecycle.sql`
separa dispositivo estable de vínculo, agrega registro v2 con núcleo privado, mantiene
registro v1 y valida acuses/resultados. Cuarenta y cinco regresiones nuevas pasan localmente.
Android compila con el nuevo RPC; aún no está desplegado ni probado con FCM real.

Quedan concretos la revocación/límite de receptores, capacidades owner/creator en
Administración, además de estilos y entrega. La entrada Android se separó después
y se verificó como se describe a continuación. Esta revisión no cierra la auditoría global.


## Entrada pública Android y navegación interna

`LauncherActivity` es la única Activity exportada y resuelve el inicio normal. Construye
un Intent nuevo para CloudActivity, sin copiar acción, URI, extras ni parámetros del
remitente. MainActivity queda dedicada a LAN e interna, igual que CloudActivity y el
servicio FCM. No hay apertura pública de entrega/aula por parámetros de lanzamiento.

AccessScreen ofrece Conexión local avanzada mediante navegación interna, disponible
sin sesión cloud. Las notificaciones propias siguen usando PendingIntent inmutable a
la pantalla interna. MainActivity ignora aperturas LAN cuando push_route no es local.
La validación de generación/vínculo de las aperturas cloud se conserva.

`EntryBoundaryChecks.kt` verifica el manifiesto efectivo instalado, lanza la entrada
pública con parámetros ficticios y comprueba que el destino no los recibe ni cambia
cola/aula. Después envía un PendingIntent propio y comprueba el acuse LAN legítimo y
el bloqueo al cambiar a ruta cloud. Restaura preferencias del emulador al finalizar.
No admite un emulador con conexiones reales configuradas para esta prueba.

La comprobación externa está separada en `herramientas/android_entry_audit.py`:
ADB shell (UID 2000) recibe Permission Denial / not exported al intentar MainActivity
y CloudActivity. La entrada pública ignora delivery_id, classroom_id, local y demo;
cola/aula permanecen iguales. Reporte: `artifacts/android-entry-boundary.json`.
Instrumentación completa: `artifacts/auditoria-android-entry.txt` (PASS).

Compilaciones assembleDebug/assembleDebugAndroidTest correctas, 32 pruebas JVM y
48 Python correctas. El recorrido visual actual parte del launcher, entra a DEMO
mediante un control visible y llega a LAN desde el acceso, sin parámetros de depuración.
Las capturas de acceso y LAN se inspeccionaron. Evidencia en
`artifacts/android-screens-audit/`. Sin credenciales de usuario, RPC de negocio o FCM real.

Los auxiliares USB/recorrido extendido resuelven el componente launcher publicado por
Android mediante `android_entry.py`, compatible con el componente antiguo y el nuevo.
El instalador USB referencia la entrega vigente 0.6.2 y escribe su diagnóstico en artifacts;
no se ejecutó sobre un teléfono. La revisión extendida ya no sobrescribe evidencias v0.6.1.
La APK/ZIP histórica no se sustituyó. El RPC de registro v2 no fue ejercitado en nube.

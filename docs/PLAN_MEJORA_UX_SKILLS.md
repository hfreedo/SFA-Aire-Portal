# Plan de mejora estética y de usabilidad

**Actualización:** la implementación de software de este plan se entrega en
[0.8.0](IMPLEMENTACION_UI_080.md), con sus verificaciones y pendientes físicos.
El diagnóstico y las puntuaciones siguientes conservan la línea de base 0.7.4;
el texto «esta entrega» de esa revisión se refiere a la etapa de planificación.

27/10/2026. Revisión con Impeccable 4.8.0, refactoring-ui 1.5.1 y ux-heuristics
1.6.0, instaladas en .agents/skills de este proyecto. Fuentes y commits:
[evaluación e integración](EVALUACION_SKILLS_DISENO.md).

**Estado de esta entrega:** integración de skills, revisión ejecutada y plan
con criterios de aceptación. No hay una APK nueva ni una recomposición aplicada
todavía. La línea de base sigue siendo Android 0.7.4. Este documento convierte
los hallazgos en trabajo implementable, sin presentar la planificación como una
mejora visual ya terminada.

## Resultado de la revisión

La base funcional tiene identidad reconocible, tres destinos Android claros,
separación entre simulación y dato real y una prueba cloud rápida ya existente.
Conviene conservarlos. La APK sigue sin resolver bien la importancia relativa
de datos, acciones y ayuda. El portal está más maduro visualmente; necesita
refinamientos y recuperación de fallos, no una sustitución completa.

Los hallazgos principales son:

1. **Android: misma importancia para demasiados controles.** Revisar avisos,
   información, actualizar y desplegables se parecen en forma y tamaño. La
   tarjeta de estado domina los sensores. No es un problema de elegir otra fuente.
2. **Android: densidad y repetición.** Aula, institución, título y estado se
   acumulan; Ajustes ocupa demasiado para explicar un único registro. Con letra
   ampliada el apilado es correcto, pero aumenta el recorrido antes de completar
   la lectura. No se debe corregir reduciendo la letra.
3. **Controles propios con acabado irregular.** Selector de opciones como
   botones grandes, interruptor cuyo círculo apagado pierde contorno, radios
   iguales para funciones distintas y espaciado implícito por cada TextView.
4. **Portal: demasiada cabecera antes de la tarea.** En ventana estrecha se
   apilan navegación, contexto y bandas. En Avisos se repite el título. En
   administración DEMO aparecen textos que piden actualizar datos que esa vista
   nunca va a consultar; Arduino DEMO queda en «Comprobando…».
5. **Recuperación ante recursos no disponibles.** La pestaña antigua de 8767
   quedó en blanco al cargar el laboratorio con el servidor detenido. La consola
   indicó fallo de precarga CSS. Una prueba HTTP confirmó conexión rechazada;
   no se atribuye el fallo a un CSS inexistente en el build actual. El build
   nuevo en 8894 sí cargó Arduino, administración y laboratorio. Falta una
   recuperación comprensible ante recursos diferidos/red no disponibles.

El selector web Origen observado ya tiene menú tematizado, selección y marca.
Se retira la afirmación genérica «todos los selectores carecen de estilo».
Su teclado, límites del contenedor y variantes largas aún deben revisarse.

## Qué se comprobó

| Superficie | Evidencia de esta revisión | Límite |
| --- | --- | --- |
| Android 0.7.4 | AVD SFA_Aire_Visual_API30, 720 × 1600 px, 360 × 800 dp. Acceso, Mi aula, Avisos, Ajustes y detalles con fuente 100 % y 130 %. Recorrido PASS. | DEMO; no sesión real, no envío FCM, no A02 físico. |
| Portal que conservaba la pestaña | Acceso, aulas, avisos, historial y selector Origen en ventana estrecha; error al cargar laboratorio. | Servidor 8767 detenido; contenido anterior en memoria. No representa un servidor actual en ejecución. |
| Portal actual | npm run build correcto; build estático en 127.0.0.1:8894. Aulas, Arduino, administración, Personas y laboratorio, sólo DEMO. | Sin API local en ese servidor de revisión; no cuentas reales ni USB. |
| Componentes y permisos | Lectura de pantallas Kotlin, AireUi, WorkspaceLayout, CloudActivity, WorkspaceActions y fuentes React. | Análisis de código no equivale a completar esos recorridos autenticados. |

Capturas del portal: ../Branding/UX/revision-skills/. Capturas nuevas Android:
../artifacts/android-074/. Para compartir sólo imágenes ficticias se copiaron
las pantallas principales a ../Branding/UX/revision-skills/android/.
La captura del acceso web puede contener autocompletado local: no publicarla.

No se activaron hooks. Se ejecutó el cargador context de Impeccable una vez.
Para Android se aplicó su revisión nativa, en un contexto, sin detector DOM ni
subagentes; el detector web no certifica Views. La revisión del portal usa los
criterios de Wondel y observación manual; no se presenta como una ejecución
completa del comando critique web de Impeccable.

## Diagnóstico reproducible de Android

Evaluaciones de inspección, no métricas de usuarios ni certificaciones. Sólo
puntúan el alcance observado; no seguridad, fiabilidad FCM ni usabilidad física.

### refactoring-ui: 4/10

Regla de la skill: round(criterios satisfechos / 8 × 10).

| Diagnóstico | Cumple | Evidencia / trabajo necesario |
| --- | --- | --- |
| Jerarquía al desenfocar o reducir | No | Las superficies de estado y botones auxiliares compiten con datos. |
| Jerarquía que no dependa del color | No | Faltan diferencias de forma/agrupación/acción; repetir verde no ordena funciones. |
| Espacio que indique relaciones | No | Padding de cada texto más márgenes automáticos produce ritmo poco intencional. |
| Etiquetas subordinadas a valores | No | Temperatura/MQ135 y varias cabeceras tienen peso elevado y parecido. |
| Escala consistente de espaciado | No | Hay medidas aisladas de 3/7/9/13/14/18/22 dp sin roles claros. |
| Ancho de lectura contenido | Sí | Panel de 360 dp, sin líneas extensas. No extrapolar a tablet. |
| Contraste de colores principales | Sí | Pares principales comprobados en contrastes.json; quedan estados interactivos. |
| Elevación adecuada | Sí | Predominio plano sin sombras que hagan flotar todo. El problema es jerarquía, no falta de sombras. |

3/8 → 4/10. Para llegar a 10/10 deben pasar las cinco filas restantes y repetirse
la inspección con los estados faltantes. No basta cambiar valores para obtener
una puntuación nominal.

### ux-heuristics: 6/10, provisional

Diagnóstico rápido de la skill: partir de 10 y descontar por filas fallidas,
ponderando su severidad. No sumar dos veces el mismo fallo.

| Fila | Resultado |
| --- | --- |
| Identidad y página reconocibles | Cumple en las vistas observadas. |
| Acción principal evidente | Falla menor, severidad 2: ayuda y acciones similares; −1. |
| Navegación clara | Cumple: tres destinos etiquetados y selección visible. |
| Buscar | No aplica al recorrido de una sola aula; no añadir buscador decorativo. |
| Mostrar qué sucede | Falla mayor de presentación, severidad 3: la actualización global no explica por sí sola vigencia ni cobertura del registro; −2. No implica que el código oculte la antigüedad. |
| Errores útiles | Cumple por inspección de código: reintento y conservación de nota. Revalidar en ejecución con fallo controlado. |
| Cancelar / volver | Cumple en navegación y diálogos revisados. |
| Sin hover | Cumple en el recorrido táctil. |
| Controles etiquetados | Cumple en las pantallas y árbol de vistas observados. |
| Evitar dudas innecesarias | Falla menor, severidad 2: registro, actualizar y permisos repiten decisiones; −1. |

El 6/10 es una estimación con alcance declarado. Para cerrar este bloque hay que
recomponer acciones, separar los estados de app/medición/notificación y validar
el registro con una cuenta real y dos aulas. No prometer «nunca falla».

### Impeccable: evaluación nativa A, 24/40

| Heurística de Nielsen | 0–4 | Motivo principal |
| --- | --- | --- |
| Visibilidad del estado | 2 | Hay estado y vigencia, pero compiten y no resumen bien el alcance push. |
| Lenguaje del usuario | 3 | Directo en tareas principales; detalles de registro aún técnicos. |
| Control y salida | 3 | Cancelar y navegación disponibles; falta verificar Back/teclado en todos los casos. |
| Consistencia | 2 | Misma identidad; roles de controles poco diferenciados. |
| Prevención de errores | 3 | Capacidades y sesión verificadas, nota opcional; falta ensayo multiaula. |
| Reconocimiento | 2 | Destinos claros, configuración del teléfono todavía exige interpretar estados. |
| Eficiencia | 2 | Recorrido simple disponible; exceso de bloques y desplazamiento. |
| Minimalismo | 1 | Botones/superficies repetidos y encabezados competidores. |
| Recuperación | 3 | Reintento y nota conservada en código; no todos los fallos ejecutados. |
| Ayuda | 3 | Información de sensores contextual; presentación demasiado dominante. |

Carga cognitiva: fallan foco único, jerarquía y separación de decisiones en
Ajustes (3 de 8, moderada según la guía). La navegación fija no se cuenta como
una decisión simultánea con todos los controles del contenido.

Personas de revisión, sin fingir entrevistas:

- Docente que abre un aviso: identificar aula y pendiente debe preceder a los
  detalles de entrega; compartir no debe parecer obligatorio.
- Estudiante que presenta desde otra PC: «receptor», cuenta y equipo USB no
  deberían exigir explicar la arquitectura antes de conectar.
- Persona con letra ampliada: conservar tamaño legible y permitir saltos de
  línea; reducir redundancia antes de reducir tipografía.

No se necesitan nuevas respuestas sobre propósito o identidad: ya fueron
expresados por el usuario. Questions skipped: objetivos y límites confirmados.

## Trabajo por prioridad e impacto

P0 significa bloqueo del recorrido; P1, dificultad relevante; P2, refinamiento.
La auditoría anterior usaba P0 para algunos problemas de jerarquía: aquí se
normalizan como P1 para no confundirlos con una tarea imposible de completar.

| Orden | Prioridad / impacto | Trabajo y archivos principales | Cierre observable |
| --- | --- | --- | --- |
| A | P0 / continuidad | Capturar fallos de carga diferida y ofrecer recuperación. RemoteWorkspace.tsx / portal-entry.tsx; revisar caché HTML/assets junto con servidor_pc/main.py. | Interrumpir carga del laboratorio/Arduino no borra toda la app; causa y salida visibles; sin recarga automática infinita ni pérdida silenciosa de formularios. |
| B | P1 / alto, las tres pestañas | Recomponer sistema común y pantallas Android juntas. AireUi.kt, WorkspaceLayout.kt, CloudActivity.kt, ui/screens/*.kt y CareDialogs.kt. | Datos protagonistas, tres roles de acciones, menos repetición, selector/interruptor/diálogos coherentes. Antes/después de todas las pestañas. |
| C | P1 / alto, confianza | Separar actualización de app, vigencia de medición, permiso Android y registro efectivo. SettingsScreen.kt, CloudActivity.kt y WorkspaceActions.kt. | Cambiar aula no deja una confirmación visual engañosa. Ver aula efectiva, estado y siguiente acción sin adivinar. No sustituir confirmación backend por estado local. |
| D | P1 / alto para presentación | Administración/Arduino DEMO: estados terminales de ejemplo, no «Comprobando…» ni pedir una consulta deshabilitada. ArduinoScreen.tsx, AdministrationScreen.tsx. | Explorar el ejemplo explica la tarea sin fingir equipos conectados, personas o comprobaciones reales. |
| E | P2 / medio | Portal: cabecera compacta, eliminar títulos duplicados, bandas de estado proporcionadas y grupos administrativos. RemoteWorkspace.tsx, portal-theme.css, pantallas de cada función. | 360/565/1280 px, zoom 200 %, contexto identificable y contenido útil; alertas importantes siguen visibles. |
| F | P2 / medio | Movimiento y detalle: tipografía óptica, iconos, selectores, scroll, foco, animaciones. Componentes compartidos de cada plataforma. | Transiciones con propósito, sin desplazamientos inesperados ni contraste perdido. Normal y movimiento reducido. |
| G | P1 / salida de entrega | APK y portable con fuentes/build/manifiesto consistentes. Herramientas de empaquetado existentes. | Probar exactamente el archivo descargable desde extracción limpia; no anunciar otra release por sólo compilar. |

Orden de dependencias: A puede resolverse sin rediseñar; B define los componentes
usados por C. D y E reutilizan la estructura actual. F se ajusta al resultado
compuesto, no antes. G se cierra tras la matriz de aceptación.

### Alcance funcional que merece una decisión separada

Actualmente notificationRegistered(room) compara cloud_push_room con el aula
seleccionada. Hay que comprobar con dos aulas qué registros mantiene realmente
el backend y qué cobertura espera cada persona. No afirmar que seleccionar aula
equivale a registrar notificaciones, ni que ya existe suscripción a todas sus
aulas. Un eventual registro automático/multiaula debe ser otra tarea funcional,
con permisos, cuotas e integración; no esconderla en un cambio de CSS/Kotlin UI.

La necesidad expresa se conserva: los avisos deben llegar a todas las personas
registradas y autorizadas para el aula. «Todos» no autoriza avisar a miembros de
otras aulas ni habilitar simulaciones sin consentimiento.

## Recorridos de referencia

1. **Consulta:** abrir → ver aula → reconocer REAL/SIMULACIÓN → leer temperatura,
   señal MQ135 y humedad → distinguir actual/histórico. Sin configuración inicial
   técnica para una persona que sólo consulta.
2. **Aviso:** tocar notificación → aviso y aula correspondientes → Marcar atendido.
   Compartir es independiente; nota opcional; sin códigos, órdenes o protocolos.
   Atender no cambia la medición ni significa que todos lo hayan recibido.
3. **Configurar teléfono:** Ajustes → ver aula efectiva y causa si falta algo →
   acción necesaria → confirmación real. La preferencia de simulación distingue
   cambio pendiente de cambio guardado.
4. **Conectar maqueta:** administrador en PC local → aula → puerto COM y refrescar
   → conectar → lectura reciente y sincronización por separado. No descargar
   credenciales manualmente para el recorrido normal ya simplificado.
5. **Administrar:** aula → Personas → agregar/invitar → estado de invitación y
   permisos. No mezclar alta de personas con PC. Mantener control por backend.
6. **Probar push:** administrador → Laboratorio → aula → Enviar aviso de prueba
   → ver resultado por etapa. Esta función ya existe: refinarla, no duplicarla.

## Matriz para aceptar la implementación

| Área | Casos requeridos | Evidencia de cierre |
| --- | --- | --- |
| Lecturas | Real y simulada; actual, vencida, sin datos; DHT inválido; MQ sin referencia | Capturas nativas/web con valores/origen/hora correctos. No datos inventados fuera de fixture explícito. |
| Avisos | Ninguno, pendiente, atendido; permiso insuficiente; entrega fallida/omitida | Acción entendible, razón al bloquear, fallo visible. Python de integración si se modifica recorrido de alertas. |
| Teléfono | Confirmado, pendiente, permiso desactivado, preferencia sucia, token fallido, dos aulas | Fixture visual más ensayo real diferenciado. Sin declarar recepción FCM por un mock. |
| Formularios | Teclado, Back/Escape, Cancelar, error de red, texto conservado, nombres largos | Recorrido ejecutado; error junto a acción; sin botones fuera de pantalla. |
| Accesibilidad | Android 100/130 %, controles 48 dp; web foco/teclado/zoom; contraste y movimiento reducido | Capturas y comprobaciones del resultado, no sólo del código. |
| Movimiento | Cambios repetidos de pestaña, interrupción, detalles, retorno desde notificación | Video del emulador; perfil y sensación en A02 separados y pendientes si no está disponible. |
| Entrega | assembleDebug y pruebas Android; npm build y revisión; portable limpio | Hashes/versiones exactos; no incluir sesión, claves privadas, mediciones ni secretos. |

La revisión de esta fecha cierra la fase de diagnóstico y planificación, no las
filas de implementación A–G. El primer lote debe resolver A y recomponer B/C;
no generar otra APK anunciada como «pulida» por modificar sólo radios o tiempos.
La especificación visual aplicable está en [CRITERIOS_DISENO_UI](CRITERIOS_DISENO_UI.md).

No se requieren servicios nuevos, migración de sensores, cambio de permisos ni
facturación para ejecutar este plan. Los pendientes físicos/cloud permanecen
identificados; no se han enviado avisos ni creado cuentas durante la revisión.

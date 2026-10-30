# Mi aula: lectura local en vivo — 28/10/2026

## Problema

Conexión Arduino consultaba el receptor local, pero Mis aulas siempre mostraba aire_overview en Supabase. La muestra normal se guarda en nube cada 60 s y el portal consultaba cada 60 s. La suma de intervalos y el ciclo de sincronización podían mostrar datos de varios minutos y Lectura vencida pese a tener USB activo.

## Cambio local

El portal instalado, con sesión administradora del aula, consulta el endpoint de estado local cada segundo mientras Mis aulas está visible. Reutiliza la autorización existente del servidor: el aula debe coincidir con la asignación y el usuario debe tener permisos administrativos. No utiliza la clave de control local en el navegador ni amplía el acceso a observadores/docentes.

Solo sustituye visualmente la muestra de la misma PC, aula y fuente; preserva muestras de otras PC y las simulaciones como fuentes distintas. Usa la fecha original de recepción de Arduino, nunca la hora de la consulta. La etiqueta En vivo · Esta PC distingue esta medición de Muestra sincronizada.

Después de 10 s sin muestra o ante error de consulta, los valores locales pasan a históricos. Cambiar sesión/aula invalida resultados anteriores; consultas pendientes se descartan al salir. No consulta con la pestaña oculta ni solapa solicitudes.

La copia cloud, el historial, los incidentes compartidos, Firebase/FCM y Android conservan su recorrido y límites. No se cambió el muestreo cloud ni se publicó Hosting o un release nuevo. La mejora queda aplicada a interfaz_web/dist, servida por el panel local existente; no requiere reiniciar el Arduino ni el receptor.

## Validación

- npm run build correcto.
- Seis pruebas Node: fecha de muestra real, aislamiento entre aulas/fuentes, reemplazo selectivo sin mutar nube, cambio de aula, datos vencidos/futuros/no disponibles, MQ135 conservado ante DHT inválido.
- Comando: node --test interfaz_web/qa/local-observation.test.mjs.
- Revisión visual y comparación con el Arduino real: ver evidencia en artifacts/mi-aula-local-20261028.*.

Comprobación real completada en navegador autenticado: la hora de muestra avanzó de 15:25:10 a 15:25:42 sin pulsar Actualizar, con antigüedad de 0–1 s. Captura: 23 °C, 55 %, MQ135 6 ADC y estado Falta referencia. Es una lectura real, no el fixture de QA. El estado Falta referencia sigue siendo correcto: no se configuró una calibración experimental.

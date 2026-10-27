# Auditoría visual de Android 0.7.4

Fecha: 27/10/2026. La APK se ejecutó de nuevo en el AVD propio API 30,
720 × 1600 px, densidad 320 (360 × 800 dp), letra al 100 %.
No hay teléfono físico conectado. La evaluación corresponde a la aplicación
nativa en ejecución; la sensación de movimiento y la adaptación final al A02
requieren su comprobación en ese dispositivo.

Informe visual offline: [capturas y anotaciones](../Branding/UX/auditoria-android-074/informe.html).
Capturas originales, XML de vistas y medidas en esa misma carpeta.

## Dictamen

0.7.4 tiene controles más coherentes y movimiento implementado, pero todavía no
alcanza el acabado visual solicitado. Compartir paleta y redondeados no basta:
la jerarquía de superficies y acciones sigue siendo débil. La apariencia de
plantilla proviene de decisiones repetidas sin atender al propósito de cada
elemento: cápsulas, fondos grandes y tipografía de peso parecido.

La revisión anterior fue principalmente funcional y de componentes. Faltó una
evaluación transversal de composición, densidad, proporción y detalle. Un pedido
general de mejora debe incluir ese trabajo; no exige que el usuario señale cada
defecto ni se justifica una mejora pequeña por la amplitud del pedido.

## Hallazgos y prioridades

| Prioridad | Hallazgo observado | Corrección propuesta |
| --- | --- | --- |
| P0 | Acciones principales, secundarias, ayuda y desplegables tienen prácticamente el mismo tamaño y silueta. | Tres tratamientos por función: acción principal rellena; secundaria discreta; ayuda/desplegable como fila ligera. Conservar áreas táctiles cómodas. |
| P0 | La tarjeta de estado y sus controles dominan la primera vista; la información ambiental queda subordinada. | Estado compacto con prioridad clara cuando hay alerta, datos como centro visual, acceso al aviso integrado. No reducir la legibilidad ni ocultar urgencia. |
| P0 | Un mismo radio de 18 dp se utiliza para tarjetas, campos, botones, selector y diálogos. | Gramática por función: controles 10–12 dp, tarjetas 16 dp, diálogos 20 dp; cápsulas para etiquetas/indicador. Valores de partida para validar visualmente. |
| P1 | En Avisos se acumulan nombre del aula, institución, título de sección, contador y nombre del aula de nuevo en la tarjeta. | Una cabecera de sección y un contexto de aula compacto. Repetir el aula dentro de la tarjeta sólo cuando sea necesario para distinguir avisos de varias aulas. |
| P1 | Espaciado automático de cada texto más márgenes de los contenedores produce intervalos poco intencionales. | Ritmo de 4/8/12/16/24 dp según relación entre contenidos; retirar padding genérico de textos y definirlo en cada composición. |
| P1 | En datos vencidos, las tarjetas paralelas pueden terminar a alturas diferentes por el texto auxiliar del MQ135. | Igualar la altura natural de las dos celdas en horizontal y alinear valores/unidades; mantener el apilado con letra ampliada. Evitar alturas rígidas que recorten. |
| P1 | El interruptor apagado pierde definición sobre la tarjeta blanca: el tinte blanco también elimina el contraste del borde del círculo. | Mantener borde visible del círculo y comprobar estados activo/inactivo/deshabilitado sobre el fondo real. La captura DEMO por sí sola no representa el estado habilitado. |
| P1 | El selector ya es propio, pero sus opciones y Cancelar siguen pareciendo una colección de botones grandes. | Filas de selección con separación limpia y marca a la derecha; fondo de selección contenido; Cancelar como acción terciaria. |
| P1 | En la nota de atención se repite “Nota opcional” y se añaden frases de registro que dan peso al formulario. | Título breve, una sola aclaración y nota opcional. Conservar la advertencia pertinente de que atender no cambia la medición. |
| P2 | El glifo Unicode ⓘ no tiene exactamente la misma geometría que los iconos dibujados de la app. | Una sola familia de iconos, con tamaños ópticos, grosor y alineación revisados. Separar área táctil de tamaño visible. |
| P2 | Textos españoles conviven con fechas/decimales del idioma del emulador. | Definir la política de localización. No asumir que todos los equipos están configurados en español. La captura inglesa no demuestra cómo se verá el formato en el A02. |
| P2 | La prueba de interpolación no determina por sí sola si el movimiento se siente refinado. | Revisar continuidad, dirección, sincronía y tiempo de lectura. Perfilar tiempos de fotograma en el A02 cuando esté disponible. |

## Medidas que explican el peso visual

En la captura nueva de Mi aula:

- «Revisar avisos», «Información de sensores» y «Actualizar aula»: **48 dp de alto**.
- Las dos acciones auxiliares inferiores ocupan **107 dp** desde el borde superior
  de la primera hasta el borde inferior de la segunda, incluido el intervalo.
- El texto de antigüedad reserva **40 dp**. El tamaño visible del texto y su área
  de interacción deben distinguirse al recomponerlo.
- Nombre del aula: caja de texto de **35,5 dp** de alto. «Revisar ambiente»: **34,5 dp**.
  Dos encabezados de importancia distinta compiten con una escala casi igual.

Son dimensiones de vistas de esta captura y configuración, no mediciones físicas
universales del teléfono. `mediciones.json` conserva bounds y etiquetas de origen.

## Dirección de composición

**Mi aula:** cabecera compacta de aula e institución; estado ambiental con origen
y antigüedad; dos métricas protagonistas; humedad integrada; ayudas discretas.
La alerta mantiene contraste y nombre explícito, pero no necesita una gran
superficie con varios controles de igual peso.

**Avisos:** título de sección, contexto del aula, resumen del aviso, fecha y estado.
Atender domina la acción del aviso pendiente; compartir y consultar entregas
quedan subordinados. Los errores de entrega y omisiones por cuota siguen visibles.

**Ajustes:** estado del registro y aula a la que pertenece; preferencia de
simulaciones con guardado explícito cuando cambie; cuenta y opciones avanzadas
como grupos de filas. El estado confirmado necesita menos explicación visible
que un registro pendiente. No añadir pasos de autorización ni protocolos.

No hacen falta gráficos decorativos ni nuevos servicios. Una gráfica sólo debe
aparecer si existe una serie real y aporta una lectura útil; no fabricar datos
para que la pantalla parezca más elaborada.

## Criterios de aceptación para la siguiente recomposición

1. Distinguir visualmente acciones primarias, secundarias y ayudas sin leer todas
   las etiquetas. No convertir cada bloque en una cápsula.
2. Una escala tipográfica y una retícula compartidas entre las tres pantallas.
   Contenido legible: cuerpo alrededor de 16 sp y apoyo 14 sp; sin resolver
   la densidad haciendo toda la letra pequeña.
3. Comparar las tres pantallas juntas y revisar luego cada una a tamaño real.
4. Datos actuales, vencidos y sin datos; aviso pendiente, atendido y sin avisos;
   registro activo, pendiente y permiso desactivado. Aulas/correos largos y letra
   al 130 %. Los estados que aún no se recorran se marcan pendientes.
5. Revisar selección, foco, teclado, scroll, pulsación, cancelación y transiciones.
   La comprobación de teclado y rendimiento físico no se da por terminada aquí.
6. Guardar un antes/después de la APK ejecutada, con la misma configuración y
   datos, y comprobar que el acabado mejora antes de publicar una nueva entrega.

## Alcance de las capturas

01–05: recorrido nuevo de acceso/Mi aula/Avisos/Ajustes y detalles en DEMO.
06: componente de Ajustes con registro confirmado y cuenta ficticia; no es una
sesión real ni una pantalla completa autenticada.
07: lectura vencida inyectada sólo en el fixture DEMO.
08: selector real con aulas ficticias y callback aislado.
09: formulario real de atención con callbacks ficticios.

No se registró un teléfono, modificó un aula, atendió un incidente real ni envió
FCM. Esta auditoría no cambia la APK publicada ni el sistema operativo del usuario.

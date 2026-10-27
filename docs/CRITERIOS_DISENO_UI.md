# Criterios para la siguiente iteración visual

Implementación y alcance actuales: [entrega 0.8.0](IMPLEMENTACION_UI_080.md).
Los valores siguientes son el criterio de partida; la validación de la entrega
distingue lo aplicado de los estados físicos y de accesibilidad aún pendientes.

27/10/2026. **Especificación de implementación pendiente**, no descripción de una
APK nueva. Aplicar por componentes y revisar juntos Mi aula, Avisos y Ajustes.
Preservar marca, propósito, contratos y reglas del producto de PRODUCT.md.

## Dirección

Modo Operate: la persona consulta una medición, reconoce un aviso o configura
su teléfono. Identidad salvia contenida, superficies claras, datos protagonistas
y controles Android familiares. El portal comparte roles y lenguaje; no necesita
copiar dimensiones de la APK.

El defecto actual no es falta de adornos: es la repetición del mismo tratamiento
en elementos de importancia distinta. No resolverlo añadiendo sombras, fuentes
de exhibición, tarjetas anidadas o animaciones de entrada en cada lectura.

## Tipografía y ritmo

| Rol | Android, punto de partida | Web, punto de partida |
| --- | --- | --- |
| Valor de sensor | 32–34 sp, semibold, unidades subordinadas | 32–36 px, cifras tabulares |
| Título de pantalla | 22 sp, semibold | 26–28 px, semibold |
| Título de sección | 18 sp, medium/semibold | 18–20 px |
| Cuerpo y controles | 16 sp, normal/medium | 15–16 px, normal/medium |
| Apoyo | 14 sp, normal | 14 px, normal |
| Etiqueta de origen | 12 sp, medium, breve | 12–13 px, medium |

Usar una familia sans por plataforma. No usar pesos finos ni reducir todo para
que quepa. Quitar padding vertical automático de cada texto al recomponer cada
pantalla; asignar los intervalos a los grupos: 4/8/12/16/24/32 dp en Android.
No aplicar ese cambio global sin revisar los formularios que dependían de él.

## Superficies y formas

- Fondo de página suave; tarjetas informativas blancas con borde discreto.
- Verde relleno para la acción principal y selección. Un aviso urgente puede
  tener prioridad semántica aunque ya exista otra acción principal.
- Advertencia/alerta con icono o texto, además del color. No colorear todos los
  sensores como si sus superficies fueran botones.
- Control: radio inicial 10–12 dp; tarjeta: 16 dp; diálogo: 20 dp. Ajustar al
  componente Android adoptado. Cápsulas reservadas para etiquetas e indicador.
- Separar tamaño visible de área táctil: ayuda ligera también ocupa al menos
  48 × 48 dp de interacción en Android. En web apuntar a 44 px para controles.
- Contraste de texto normal ≥4,5:1; grande ≥3:1. Verificar también bordes,
  selección, estados deshabilitados y foco; estos no quedan certificados por
  contrastar sólo los colores principales.

## Vocabulario de componentes

| Componente | Tratamiento y comportamiento |
| --- | --- |
| Acción principal | Rellena, etiqueta con verbo, una por decisión. Mostrar progreso sin cambiar su ancho bruscamente. |
| Secundaria | Contorno o tonal contenido; no repetir un bloque de gran tamaño para cada ayuda. |
| Ayuda / actualización manual | Acción textual o icono etiquetado, foco y área táctil propios. |
| Fila de ajustes | Etiqueta, valor/estado y control alineados; explicación sólo cuando aporta una decisión. |
| Selector Android | Control nativo/Material tematizado; lista de opciones, marca seleccionada, Cancelar discreto; nombres largos legibles. |
| Selector web | Conservar StyledSelect donde ya funciona; verificar flechas, Inicio/Fin, Enter, Escape, foco y borde del menú. No reescribirlo por estética. |
| Interruptor | Silueta y estados de Android; activo/inactivo/deshabilitado distinguibles sobre la tarjeta real. |
| Desplegable de detalles | Fila ligera y chevron; no parecer otro botón principal. |
| Formulario de atención | Nota opcional una sola vez. Guardar y Cancelar, error en el mismo lugar, texto preservado al fallar. |
| Mensaje de fallo | Qué pasó, qué se conserva y siguiente acción. No dejar un botón gris sin causa. |

Revisar Material Components para Views antes de consolidar más controles propios.
No convertir la adopción en una migración a Compose ni cambiar dependencias sin
compilación, revisión de licencia y prueba de tamaño/rendimiento. La app actual
usa controles de plataforma y estilos propios; no declarar conformidad Material 3.

## Composición por pantalla

**Mi aula:** contexto de aula una sola vez → origen y estado/antigüedad compactos
→ temperatura y MQ135 alineados → humedad → ayuda discreta. Mantener el aviso
pendiente visible; no esconder urgencia para adelantar las métricas. Valores
históricos explícitos. Con letra ampliada apilar naturalmente, sin alturas rígidas.

**Avisos:** título de sección → contexto de aula compacto → pendientes primero
→ resumen, fecha y origen → Marcar atendido → Compartir como acción secundaria
→ detalles de entrega. No repetir aula dentro de cada aviso si toda la lista
ya está filtrada por esa aula. Los fallos/omisiones de entrega siguen visibles.

**Ajustes:** estado de avisos y aula efectiva → preferencia de simulación → cuenta
→ opciones avanzadas. Cuando está confirmado, evitar párrafos y botones de
reparación permanentes. Si está pendiente, mostrar la causa y una sola acción
pertinente. Guardar preferencia aparece al existir un cambio sin guardar.

**Portal:** mantener navegación y arquitectura existentes; reducir duplicados de
título y cabeceras en ancho estrecho. Una banda de demostración persistente, sin
confundirla con una alerta ambiental. En administración, listado → detalle de
aula → Personas / PC; los estados DEMO deben explicar que no consultan la nube.

## Movimiento

| Interacción | Intención | Presupuesto inicial |
| --- | --- | --- |
| Pulsación | Confirmar contacto | Ripple nativo; 100–150 ms si se necesita transición |
| Cambio de pestaña | Conservar orientación | 180–240 ms en conjunto; no sumar una salida lenta a otra entrada lenta |
| Selección / menú | Mostrar relación control–opciones | 150–200 ms, sin rebote |
| Detalles expandibles | Relacionar cabecera y contenido | 180–240 ms; revisar saltos de scroll |
| Dato recibido | Actualizar en su sitio | Sin animar la pantalla ni hacer contar cifras ficticias |
| Resultado de una acción | Confirmación legible | Estado/texto visible; no depender de la animación |

Android: respetar Eliminar animaciones. Web: prefers-reduced-motion. No agregar
loops, pulsos de alarma constantes, blur costoso o elevación al pasar por tarjetas
que no se pueden pulsar. La meta es continuidad; una transición más llamativa no
es necesariamente mejor. El A02 debe comprobar la fluidez física.

## Prueba visual de aceptación

Comparación antes/después con mismos datos, densidad, viewport y fuente; las tres
pantallas Android juntas y luego a tamaño real. Una captura bonita aislada no
cierra el trabajo. Deben pasar también las matrices del plan, foco/teclado/scroll,
movimiento reducido y texto largo. Dejar pendientes explícitos cuando no exista
dispositivo o sesión autorizada para verificar un estado real.

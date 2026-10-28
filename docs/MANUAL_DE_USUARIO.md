<a id="cap_0"></a>

# Manual de usuario de SFA Aire

**[Descargar PDF](manual-usuario/Manual_de_usuario_SFA_Aire.pdf?raw=1)** ·
[Word editable](manual-usuario/Manual_de_usuario_SFA_Aire.docx?raw=1) ·
[Paquete completo](manual-usuario/Manual_de_usuario_SFA_Aire_2026-10-27.zip?raw=1)

Puede leer el manual completo aquí mismo. Para el HTML sin conexión con imágenes
ampliables, descargue y extraiga el paquete y abra el archivo HTML en su navegador.
GitHub muestra el código del HTML si lo abre como archivo del repositorio.
El paquete contiene documentación, no el programa ni cuentas o credenciales.


Instalación y puesta en funcionamiento del monitoreo ambiental de aulas

Edición del 27 de octubre de 2026. Windows y portal 0.8.0. Android 0.8.2 disponible en la entrega local del responsable.

Esta guía permite que una persona con los archivos oficiales y un acceso autorizado pueda instalar el sistema, activar su cuenta, consultar las mediciones y recibir o atender avisos. También explica las tareas del administrador y cómo conectar la maqueta a una PC.

Los archivos por sí solos no crean una cuenta ni conceden permisos. Para ingresar necesita una invitación del administrador o una cuenta ya asignada a un aula. La infraestructura de esta instalación está preparada; crear una institución o un proyecto cloud nuevo requiere intervención técnica independiente.

<img src="manual-usuario/capturas/01-sfa-aire-verde-transparente.png" alt="SFA Aire" width="180">

Qué encontrará: recorridos numerados, resultados esperados, explicación de cada apartado, capturas de referencia y soluciones a problemas frecuentes. Los nombres en negrita corresponden a controles o mensajes del sistema.

Alcance de las imágenes: se utilizan capturas de la aplicación y del portal en demostración, emulador o pruebas controladas. Las cuentas y mediciones de ejemplo no son datos de un aula real. Las fechas de ejemplo no deben interpretarse como la fecha de su instalación.

SFA Aire es un prototipo educativo de observación ambiental relativa. El MQ135 no mide CO₂, AQI ni ppm certificadas. Las lecturas y avisos apoyan la revisión humana; no certifican salubridad ni deciden automáticamente una evacuación.

<a id="cap_1"></a>

## Contenido y formas de usar este manual

Si va a consultar desde el navegador, empiece por los capítulos 03, 05, 06 y 07. Si usará Android, continúe con 11 a 15. Si conectará una maqueta, necesita además 04 y 19 a 21. Las tareas de administración se encuentran en 16 a 18; las pruebas, en 22 y 23.

- [01 Qué hace el sistema y qué necesita cada persona](#cap_2)
- [02 Archivos requisitos y versiones](#cap_3)
- [03 Elegir entre portal app y demostración](#cap_4)
- [04 Instalar Windows y abrir el panel](#cap_5)
- [05 Activar su cuenta mediante una invitación](#cap_6)
- [06 Ingresar seleccionar aula y cerrar sesión](#cap_7)
- [07 Recorrer el portal y consultar Mis aulas](#cap_8)
- [08 Entender estados antigüedad y mediciones](#cap_9)
- [09 Consultar y atender avisos en la web](#cap_10)
- [10 Consultar el historial](#cap_11)
- [11 Instalar o actualizar Android](#cap_12)
- [12 Leer Mi aula en Android](#cap_13)
- [13 Abrir y atender un aviso en Android](#cap_14)
- [14 Organizar el archivo personal de Android](#cap_15)
- [15 Activar avisos y preferencias del teléfono](#cap_16)
- [16 Administrar aulas y sus datos](#cap_17)
- [17 Invitar personas y gestionar accesos](#cap_18)
- [18 Administrar las PC del aula](#cap_19)
- [19 Asignar esta PC y conectar Arduino](#cap_20)
- [20 Preparar la maqueta y verificar sus conexiones](#cap_21)
- [21 Configurar las reglas de la maqueta](#cap_22)
- [22 Probar una notificación desde la nube](#cap_23)
- [23 Ensayar el recorrido completo con la PC](#cap_24)
- [24 Resolver problemas de acceso lecturas y avisos](#cap_25)
- [25 Cerrar actualizar y proteger la instalación](#cap_26)
- [26 Comprobación de primera puesta en funcionamiento](#cap_27)
- [27 Glosario alcance y referencias de la guía](#cap_28)

Cómo leer los pasos: realice las acciones en el orden indicado y compruebe el resultado esperado antes de seguir. Si falta una opción, revise primero el aula y el permiso de su cuenta. Un control deshabilitado en demostración no indica necesariamente una avería.

Las capturas se incluyen como referencia visual. En GitHub puede abrir las imágenes; en el manual HTML descargado puede pulsarlas para ampliarlas. Los ejemplos no proporcionan contraseñas ni enlaces válidos de invitación.

<a id="cap_2"></a>

## 01 Qué hace el sistema y qué necesita cada persona

SFA Aire reúne temperatura, humedad y señal relativa MQ135 de una maqueta Arduino. Una PC recibe los datos por USB y los sincroniza. El portal y Android permiten consultar las aulas autorizadas; el servicio cloud envía avisos a los teléfonos registrados.

![Recorrido de uso del sistema. Esquema explicativo, no evidencia de sensores o recepción física.](manual-usuario/capturas/02-recorrido.png)

*Recorrido de uso del sistema. Esquema explicativo, no evidencia de sensores o recepción física.*

La PC y el Arduino deben permanecer encendidos para obtener nuevas mediciones físicas. Una vez guardado un evento en la nube, su envío remoto no depende del receptor PC. Poder abrir el portal con la PC apagada no significa que se estén obteniendo muestras nuevas.

| Persona | Puede hacer en su aula |
| --- | --- |
| Administrador | Consultar, atender, administrar accesos y PC, configurar reglas y ejecutar ensayos autorizados. |
| Docente | Consultar mediciones e historial y marcar avisos como atendidos. |
| Observador | Consultar los apartados disponibles; no atender ni administrar. |

Los permisos son por aula. La misma cuenta puede tener funciones diferentes al cambiar de aula. Crear aulas nuevas requiere una capacidad institucional específica: administrar un aula no garantiza ese permiso.

Resultado esperado: cada persona identifica si necesita solo navegador, app Android o una PC con Arduino. Los teléfonos no se registran como PC receptoras.

<a id="cap_3"></a>

## 02 Archivos requisitos y versiones

Use los archivos oficiales de https://github.com/hfreedo/SFA-Aire-Portal/releases. Identifique el nombre exacto antes de descargar: la página puede mostrar varias entregas históricas.

| Elemento | Archivo o requisito |
| --- | --- |
| Windows | SFA_Aire_Windows_0.8.0_portable_x64.zip. Windows 10 u 11 de 64 bits; compilado y verificado en Windows 11 x64. |
| Android de este manual | SFA_Aire_0.8.2.apk, disponible en Entregas de esta instalación. Solicítela al responsable. Android 8 o posterior. |
| Consulta web | Navegador actualizado e internet; no necesita instalar el receptor para consultar la nube. |
| Avisos Android | Internet, servicios de Google Play, permiso de notificaciones y registro del teléfono en el aula. |
| Maqueta | Placa y firmware compatibles, sensores preparados, cable USB de datos y controlador USB si corresponde. |

El ZIP Windows 0.8.0 conserva la APK 0.8.0 de su entrega original. Para las funciones Android que describe este manual, utilice la APK 0.8.2 separada. Una descarga Wi-Fi desde un portable antiguo puede entregar una APK anterior; compruebe la versión en Ajustes. Al verificar los releases el 27 de octubre, Android 0.8.1 estaba publicado por separado y 0.8.2 todavía no aparecía: no busque un release 0.8.2 si aún no está disponible.

El portable incluye sus componentes de ejecución: no necesita instalar Python ni Node.js para usarlo. La placa Arduino requiere su firmware y, según el modelo, un controlador USB preparado por el responsable técnico.

Los ejecutables Windows no tienen firma Authenticode. La APK utiliza firma piloto debug; no es una publicación de producción en Play Store. Compruebe la procedencia y los hashes del release. No desactive globalmente las protecciones de Windows o Android para instalar.

Si recibió únicamente fuentes y archivos de desarrollo, solicite el portable al responsable. Los scripts de compilación y las migraciones de base de datos no forman parte del primer uso de una persona usuaria.

<a id="cap_4"></a>

## 03 Elegir entre portal app y demostración

El acceso web público es https://sfa-aire-aulas.web.app/remoto. Permite consultar aulas, avisos e historial y usar las funciones administrativas autorizadas. No abre el USB del teléfono ni convierte cualquier navegador en receptor Arduino.

En Windows, el panel abre el portal local de esa instalación. Es el recorrido apropiado para asignar la PC y controlar el puerto USB. Abra siempre desde el panel: el puerto local puede variar si otra instalación está usando el habitual.

Android está pensado para consultar el aula y recibir avisos. Iniciar sesión en un navegador no inicia sesión automáticamente en la app, ni al revés. Use su propia cuenta en ambos.

1. Para explorar sin cuenta, pulse **Explorar demostración sin cuenta** en web o **Explorar demostración** en Android.
2. Busque el rótulo **DEMOSTRACIÓN** y las etiquetas **SIMULACIÓN**.
3. Recorra las pantallas. Los datos son ejemplos y las acciones reales permanecen restringidas.
4. Salga de la demostración para iniciar sesión con su cuenta.

Es importante distinguir dos situaciones: la demostración de interfaz no envía notificaciones ni cambia la nube; un ensayo administrativo real del Laboratorio sí puede guardar datos sintéticos y enviar un push real rotulado SIMULACIÓN.

Resultado esperado: sabe si está observando una maqueta real, explorando ejemplos o ejecutando una prueba autorizada. No use una demostración como evidencia de que el teléfono quedó registrado.

<a id="cap_5"></a>

## 04 Instalar Windows y abrir el panel

1. Descargue el ZIP portable indicado en el capítulo 02.
2. En el Explorador de Windows, haga clic derecho sobre el ZIP y seleccione **Extraer todo**. Elija una carpeta propia con permiso de escritura, por ejemplo Documentos\SFA_Aire.
3. Abra la carpeta extraída y ejecute **Panel SFA Aire.exe**. Conserve junto al panel todos los archivos y subdirectorios del paquete.
4. Pulse **Abrir SFA Aire**. El panel inicia el receptor de esa carpeta y abre el navegador.
5. En el portal, ingrese con su cuenta o explore la demostración. Para una maqueta, continúe en el capítulo 19.

No ejecute el programa desde la vista del ZIP ni copie únicamente el EXE. No mezcle archivos de distintas versiones en una carpeta usada. El primer acceso y la primera vinculación de PC necesitan internet.

| Control del panel | Para qué sirve |
| --- | --- |
| Abrir SFA Aire | Abre el sistema y pone en marcha el servidor de esta instalación. |
| Conectar Arduino | Lleva al recorrido del portal local para vincular y conectar la placa. |
| Abrir demostración | Abre ejemplos aislados para conocer la interfaz sin nube. |
| Instalar por Wi-Fi | Ofrece temporalmente la APK incluida; necesita PC y teléfono en la misma red. |
| Actualizar estado | Comprueba el estado de los componentes del panel. |
| Detener monitoreo | Detiene el receptor y la demostración de esta carpeta. |

Al cerrar el panel, elija **Cerrar panel y mantener monitoreo** si la PC seguirá adquiriendo datos, o **Detener monitoreo y salir** para terminar. Cerrar una pestaña del navegador no detiene por sí solo el receptor.

Resultado esperado: aparece la pantalla de acceso o la demostración. El receptor escucha en localhost por defecto; no necesita abrir puertos del router. Si no abre, revise el diagnóstico del panel antes de intentar otra instalación.

<a id="cap_6"></a>

## 05 Activar su cuenta mediante una invitación

El alta no es libre. Solicite al administrador una invitación para su correo y su aula. El administrador comparte un enlace privado o QR; el sistema no envía correo automáticamente. El enlace vence en una hora y puede revocarse.

1. Abra el enlace privado que recibió. Si tiene el enlace copiado, use **Tengo una invitación**, péguelo completo y pulse **Continuar**.
2. Si es una cuenta nueva, verá **Activa tu cuenta**. Compruebe el **Correo de la invitación**; no se modifica desde ese formulario.
3. Escriba una contraseña propia en **Crea tu contraseña** y repítala en **Confirma tu contraseña**. Debe tener entre 12 y 128 caracteres. No utilice la contraseña ilustrada ni se la envíe al administrador.
4. Pulse **Crear contraseña y entrar** y espere la confirmación. El acceso al aula se asigna al aceptar.
5. Si ya tiene cuenta, verá **Acepta tu invitación**: use su contraseña actual y pulse **Aceptar y entrar**. La invitación no cambia esa contraseña.

![Alta por invitación en una prueba controlada. El correo example.test es ficticio; no se muestra un enlace ni QR utilizables.](manual-usuario/capturas/03-1440-alta.png)

*Alta por invitación en una prueba controlada. El correo example.test es ficticio; no se muestra un enlace ni QR utilizables.*

En Android, **Tengo una invitación** abre el navegador. Complete allí la activación, vuelva a SFA Aire e ingrese con su correo y contraseña. La sesión del navegador no se transfiere a la app.

Si el enlace venció, fue revocado o no corresponde a su correo, solicite uno nuevo. Si olvidó una contraseña existente, contacte al administrador: la pantalla actual no ofrece recuperación autoservicio. Aceptar una invitación no activa los avisos del teléfono; complete el capítulo 15.

<a id="cap_7"></a>

## 06 Ingresar seleccionar aula y cerrar sesión

1. Abra el portal público o el portal que inicia el panel Windows.
2. En **Ingresar al monitoreo**, complete **Correo electrónico** y **Contraseña** y pulse **Ingresar**.
3. Espere a que se verifiquen la cuenta y las aulas. Una pantalla de carga o error no significa que tenga cero aulas.
4. Elija el aula en **Aula seleccionada**. Compruebe su nombre antes de leer, atender o configurar algo.
5. Use **Actualizar** para solicitar el estado verificado cuando lo necesite.

Si la cuenta no tiene aulas, solicite al responsable que revise la invitación y la membresía. Tener cuenta no implica acceso a todas las aulas. Si ingresa con otra cuenta, cierre primero la sesión actual.

![Acceso Android 0.8.2 ejecutado en emulador. Los campos de cuenta son equivalentes al acceso web.](manual-usuario/capturas/04-normal-acceso.png)

*Acceso Android 0.8.2 ejecutado en emulador. Los campos de cuenta son equivalentes al acceso web.*

Ante un error de correo o contraseña, revise los datos antes de reintentar. Si la aplicación indica falta de confirmación o acceso, solicite la revisión de su cuenta. Si hay fallo de red, recupere la conexión y use **Volver a intentar** o **Volver a ingresar**, según la pantalla.

En una PC compartida, pulse **Cerrar sesión** al terminar. En Android utilice **Cerrar sesión y desvincular teléfono**, explicado en el capítulo 25. Cerrar la ventana no garantiza el cierre de la sesión.

Resultado esperado: el nombre del aula y las opciones disponibles corresponden a su cuenta. No deben aparecer campos para introducir claves administrativas de Supabase o Firebase.

<a id="cap_8"></a>

## 07 Recorrer el portal y consultar Mis aulas

El menú reúne **Mis aulas**, **Avisos** e **Historial**. Según sus permisos también verá **Conexión Arduino**, **Administración** y **Laboratorio**. En pantalla pequeña, utilice la navegación disponible y mantenga visible el aula seleccionada.

![Portal 0.8.0 en demostración. Menú lateral, selector de aula, aviso pendiente y tarjetas de sensores.](manual-usuario/capturas/05-portal-aulas.png)

*Portal 0.8.0 en demostración. Menú lateral, selector de aula, aviso pendiente y tarjetas de sensores.*

1. En **Mis aulas**, verifique el nombre del aula y la conexión.
2. Distinga **ARDUINO REAL** de **Pruebas y simulaciones**. Las muestras físicas y sintéticas no representan el mismo origen.
3. Lea temperatura en °C, humedad en % y señal MQ135 en ADC o veces su referencia. Revise también el estado y la antigüedad de la muestra.
4. Si hay un aviso pendiente, use **Revisar avisos** o **Ver aviso**.
5. Para explorar cambios anteriores, pulse **Ver historial**.

**Esperando mediciones reales** significa que no hay muestras físicas sincronizadas para esa aula. Los guiones en las tarjetas no equivalen a un valor cero. Si hay muestras simuladas, pueden aparecer en una sección separada aunque todavía no exista Arduino conectado.

**Sin atención pendiente** significa que no hay avisos abiertos dentro del estado consultado. No demuestra que haya lectura actual ni que el ambiente sea saludable. Revise siempre fuente, vigencia y sensores.

<a id="cap_9"></a>

## 08 Entender estados antigüedad y mediciones

| Mensaje | Cómo interpretarlo y qué revisar |
| --- | --- |
| Sin variación sostenida | La regla no confirma una variación en las muestras válidas. No es una certificación sanitaria. |
| Variación sostenida | Se alcanzó el nivel de aviso durante el tiempo configurado. Revise ambiente y lectura. |
| Revisar ambiente | Se confirmó una alerta. Consulte el aviso y actúe según el procedimiento de la institución. |
| Revisar sensores | Alguna medición es inválida o se detectó un fallo. Revise alimentación, conexiones y diagnóstico. |
| Estabilizando sensor | Está en la espera inicial. No sustituye el acondicionamiento del módulo. |
| Falta referencia | El MQ135 necesita una referencia experimental válida y su confirmación. |
| Sin datos recientes | No hay una medición vigente verificable. Los valores anteriores son históricos. |
| Monitoreo detenido | La adquisición está detenida. No habrá nuevas muestras hasta reanudarla. |

El receptor USB considera vencida una lectura tras más de 10 segundos sin muestra válida. La consulta cloud permite hasta 95 segundos de antigüedad porque la sincronización normal es aproximadamente cada minuto. Son criterios de vigencia distintos; no espere que ambas pantallas actualicen al mismo segundo.

La fecha del aviso y la fecha de la lectura actual también son distintas. En Android puede tocar la antigüedad para ver la fecha exacta. Una entrega atrasada conserva su fecha; no debe interpretarse como una alerta recién medida.

El DHT mide temperatura y humedad. El MQ135 es multisensible y depende de alimentación, acondicionamiento y referencia. Un valor como 560 ADC no equivale a 560 ppm. El cociente × referencia tampoco identifica un gas.

Si se pierde la red o el sensor, no interprete el último color verde como normalidad actual. Verifique vigencia y use el canal institucional previsto si necesita comunicar una situación.

<a id="cap_10"></a>

## 09 Consultar y atender avisos en la web

1. Seleccione el aula y abra **Avisos**.
2. Use **Pendientes**, **Atendidos** o **Todos**. Revise origen, condición, fecha y nota del aviso que quiere atender.
3. Si puede realizar la acción, pulse **Marcar atendido**. La atención es directa y no obliga a escribir un comentario.
4. Si desea explicar lo realizado, use **Atender con comentario**. En **Marcar aviso como atendido**, escriba la **Nota opcional** y confirme con **Marcar atendido**. La nota admite hasta 500 caracteres.
5. Espere la confirmación y compruebe el aviso en **Atendidos**. **Cancelar** cierra el formulario sin guardar.

![Vista web de avisos con datos de ejemplo. El aviso atendido sigue conservando su origen y su fecha.](manual-usuario/capturas/06-1440-avisos.png)

*Vista web de avisos con datos de ejemplo. El aviso atendido sigue conservando su origen y su fecha.*

Si falla el guardado, el formulario conserva la nota. Lea el error antes de reintentar. Si otra persona modificó el aviso, actualice y revise su estado; no suponga que el intento anterior se guardó.

**Marcar atendido** registra una decisión humana y la comparte con las personas autorizadas del aula. No modifica una lectura, no normaliza el ambiente y no acredita una acción que usted no haya realizado. La recuperación de los sensores tampoco atiende automáticamente el aviso. Abrir un push no lo atiende.

**Compartir aviso** abre el selector del dispositivo o copia el texto si esa función no existe. Usted elige el canal y completa el envío. No hay envío automático ni confirmación de comprensión de la otra persona. Los observadores no pueden atender avisos.

<a id="cap_11"></a>

## 10 Consultar el historial

1. Elija el aula y abra **Historial**.
2. En **Origen**, seleccione **Arduino real** o **Simulación**.
3. En **Variable**, elija **Señal MQ135**, **Temperatura** o **Humedad**.
4. Pulse **Consultar últimas 60 muestras**. Espere la respuesta antes de cambiar de consulta.
5. Observe la gráfica y la tabla **Detalle de muestras**. Cada fila conserva fecha, valores, referencia y estado.

![Historial del portal en una prueba de interfaz. La gráfica representa una consulta de ejemplo.](manual-usuario/capturas/07-1440-historial.png)

*Historial del portal en una prueba de interfaz. La gráfica representa una consulta de ejemplo.*

La gráfica ayuda a reconocer variaciones. No es una vista de todas las mediciones desde la instalación ni una predicción. El botón obtiene hasta 60 muestras del origen elegido. En una pantalla pequeña puede desplazar la tabla horizontalmente.

Si cambia aula u origen, vuelva a consultar: el resultado anterior no debe atribuirse al nuevo contexto. Si no hay muestras, revise la selección y si ese origen llegó a registrar datos. La falta de filas no significa que un sensor midiera cero.

Las lecturas que se sincronizan después de un corte de red conservan su hora original. Una fecha antigua sigue siendo histórica aunque aparezca ahora en la nube. La versión descrita no ofrece un botón general de exportación del historial.

Resultado esperado: puede identificar qué variable y origen está consultando y a qué fecha corresponden los valores. Para conocer el estado actual, vuelva a Mis aulas y compruebe su vigencia.

<a id="cap_12"></a>

## 11 Instalar o actualizar Android

1. Solicite al responsable **SFA_Aire_0.8.2.apk**, disponible en la carpeta Entregas de esta instalación. Al verificar esta edición todavía no había un release público 0.8.2. Si se publica después, compruebe nombre, procedencia y versión antes de descargarlo.
2. Abra el APK en el teléfono. Si Android lo solicita, permita a esa aplicación de origen instalar el archivo. El nombre y la ruta del permiso dependen del fabricante.
3. Complete la instalación. Si tiene una versión piloto con la misma firma, instale la actualización sobre ella para conservar los datos locales.
4. Abra **SFA Aire**. Active primero su cuenta si recibió una invitación y luego pulse **Ingresar** con correo y contraseña.
5. Revise **Ajustes** y confirme que la versión es 0.8.2. Continúe con el registro de avisos del capítulo 15.

Para una descarga Wi-Fi desde Windows, coloque PC y teléfono en la misma red, pulse **Instalar por Wi-Fi** y compruebe la versión indicada como **App** antes de descargar. Escanee su QR o abra el enlace. Mantenga el servicio disponible durante la descarga; el enlace es temporal, normalmente de 30 minutos. No es el QR privado de invitación.

El portable Windows 0.8.0 incluye una APK 0.8.0. Su herramienta Wi-Fi no garantiza la versión 0.8.2. Para obtenerla, use el archivo separado proporcionado por el responsable; no cambie archivos del portable al azar.

La conexión USB del teléfono no es necesaria para instalar por Wi-Fi. Para consultar y recibir avisos cloud, no es necesario que el teléfono permanezca en la red de la PC: necesita internet y acceso al servicio.

Si Android indica incompatibilidad de firma, no desinstale de inmediato. Solicite revisión del archivo y de la instalación anterior: borrar datos o desinstalar elimina el archivo personal de avisos. Android 0.8.2 sigue siendo una APK piloto; su aceptación física en el Samsung A02 está pendiente en las evidencias de esta edición.

<a id="cap_13"></a>

## 12 Leer Mi aula en Android

La navegación inferior contiene **Mi aula**, **Avisos** y **Ajustes**. Si su cuenta dispone de varias aulas, seleccione primero la que desea consultar. La selección de aula no registra automáticamente el teléfono para todas ellas.

![Mi aula en Android 0.8.2. Captura nativa de demostración en emulador, con lectura sintética.](manual-usuario/capturas/08-normal-aula.png)

*Mi aula en Android 0.8.2. Captura nativa de demostración en emulador, con lectura sintética.*

1. En **Mi aula**, lea el nombre de la institución y del aula.
2. Compruebe el rótulo de origen y el estado. **SIMULACIÓN** identifica un ejemplo o un ensayo, no un sensor real.
3. Revise las tarjetas de temperatura y MQ135 y el valor de humedad. Los valores no disponibles no se sustituyen por cero.
4. Toque la antigüedad de la lectura si necesita su fecha exacta. Abra **Información de sensores** para consultar su interpretación.
5. Use **Actualizar aula** para solicitar una comprobación y **Ver aviso** para ir a la atención pendiente.

Si la lectura vence, consulte los datos históricos solo como diagnóstico. Actualizar la pantalla no vuelve a medir el ambiente: la nueva muestra debe llegar desde la maqueta y la PC. Si el teléfono está sin red, no puede acreditar una actualización cloud.

<a id="cap_14"></a>

## 13 Abrir y atender un aviso en Android

1. Toque la notificación de SFA Aire o abra la pestaña **Avisos**. Una notificación legítima dirige al aviso correspondiente cuando su sesión conserva acceso.
2. Elija **Pendientes** o **Atendidos** y pulse **Detalles y acciones** para desplegar la información.
3. Compruebe fecha, aula, origen y lectura asociada. Es la lectura histórica que originó o elevó el aviso, no el valor actual del ambiente.
4. Si puede atenderlo, pulse **Marcar atendido**. Para dejar explicación, use **Atender con nota** y confirme el formulario.
5. Espere la confirmación. La atención compartida se refleja en los clientes que actualicen ese aviso.

![Aviso desplegado en Android 0.8.2, emulador y datos de demostración. La lectura conserva su fecha.](manual-usuario/capturas/09-normal-aviso-expandido.png)

*Aviso desplegado en Android 0.8.2, emulador y datos de demostración. La lectura conserva su fecha.*

Los avisos antiguos pueden indicar **Sin lectura asociada conservada**. No se rellenan con la lectura de otro momento. **Detalles de entrega** permite diferenciar lo que se sabe del envío y del teléfono.

**Compartir aviso** es opcional y usa el canal que usted elija. Abrir, compartir o atender no confirma que el ambiente se haya normalizado. Para revisar el estado actual, vuelva a **Mi aula**. Si faltan permisos, se perdió la sesión o cambió el aviso, actualice y revise el mensaje antes de repetir una acción.

<a id="cap_15"></a>

## 14 Organizar el archivo personal de Android

**Pendientes** y **Atendidos** representan el estado compartido del incidente. **Archivo** es una organización personal de esa cuenta en ese teléfono. Son funciones diferentes.

1. En Avisos, despliegue **Detalles y acciones** del aviso que quiere apartar de su bandeja.
2. Pulse **Archivar en este teléfono**.
3. Abra **Archivo** para volver a encontrarlo. Puede haber un aviso pendiente allí: archivarlo no lo atiende.
4. Para recuperarlo, pulse **Restaurar en la bandeja**. Volverá a Pendientes o Atendidos según el estado compartido vigente.

![Archivo personal Android con un aviso aún pendiente. Ejemplo en emulador, sin cambios cloud.](manual-usuario/capturas/10-normal-archivo-personal.png)

*Archivo personal Android con un aviso aún pendiente. Ejemplo en emulador, sin cambios cloud.*

Archivar no elimina el incidente, no detiene notificaciones, no modifica lo que ve otra persona y no acredita atención. Antes de archivar una situación pendiente, compruebe que no está confundiendo orden de bandeja con respuesta al aviso.

El archivo no se sincroniza entre teléfonos. Se conserva al actualizar sobre una APK compatible y al volver a entrar con la misma cuenta en ese dispositivo. Borrar datos o desinstalar la aplicación lo elimina. Su límite local es de 500 identificadores.

La bandeja organiza los avisos recientes que entrega el portal, hasta 30. No es una descarga ilimitada de todo el historial institucional. Si necesita revisar un evento que no aparece, consulte al administrador y los registros disponibles.

<a id="cap_16"></a>

## 15 Activar avisos y preferencias del teléfono

1. Ingrese con su cuenta y seleccione el aula correcta.
2. Abra **Ajustes** y consulte **Avisos en este teléfono**.
3. Si figura **PERMISO ANDROID PENDIENTE**, pulse **Revisar permiso de Android** y habilite las notificaciones de SFA Aire en la pantalla del sistema operativo.
4. Si falta registro, pulse **Activar avisos en este teléfono** y espere confirmación. Si ya figura **AVISOS ACTIVOS**, compruebe el aula; no es necesario activar de nuevo.
5. Solo para participar en ensayos, active **Incluir simulaciones** y pulse **Guardar preferencia**. Mover el interruptor sin guardar no confirma el cambio remoto.
6. Verifique **AVISOS ACTIVOS** y que el aula registrada sea la que espera.

![Ajustes y detalles del registro en Android 0.8.2. Esta captura de DEMO no muestra un registro FCM real.](manual-usuario/capturas/11-normal-registro-expandido.png)

*Ajustes y detalles del registro en Android 0.8.2. Esta captura de DEMO no muestra un registro FCM real.*

En **Detalles del registro**, revise **Permiso Android**, **Registro del aula**, **Actualizar registro** y **Permisos en Android**. Si indica otra aula, revise su selección y registre la correspondiente; no suponga registro multiaula automático.

Aceptar la invitación o iniciar sesión no sustituye estos pasos. El teléfono necesita internet y servicios Google Play para FCM. Si deja de participar en ensayos, desactive simulaciones y guarde la preferencia. Permiso, registro, aceptación de Firebase y recepción son comprobaciones diferentes.

<a id="cap_17"></a>

## 16 Administrar aulas y sus datos

Este apartado corresponde a personas con autorización administrativa. Si no aparece en el menú, no intente habilitarlo mediante claves técnicas: solicite revisión del permiso.

1. Abra **Administración** y seleccione el aula.
2. En **Resumen**, use **Ver personas** o **Ver PC del aula** para comprobar su preparación.
3. Para cambiar el nombre o la institución, pulse **Editar datos**, complete **Editar aula** y use **Guardar aula**.
4. Si su cuenta tiene capacidad institucional, use **Nueva aula**, complete nombre e institución opcional y pulse **Crear aula**. El nombre admite de 2 a 100 caracteres; la institución hasta 120.
5. Pulse **Actualizar configuración** para revisar el estado y permisos vigentes.

![Resumen administrativo en un ensayo de interfaz con aulas de ejemplo.](manual-usuario/capturas/12-1440-resumen.png)

*Resumen administrativo en un ensayo de interfaz con aulas de ejemplo.*

El aula reúne sus lecturas y avisos. Las personas acceden por cuenta y permiso; la PC receptora aporta mediciones; el teléfono se registra desde Android. No son elementos intercambiables.

Crear un aula no crea su montaje físico ni registra teléfonos automáticamente. Para dejarla operativa, revise personas autorizadas, PC vinculada si adquirirá sensores, reglas y registro de cada teléfono. Si falta **Nueva aula**, puede deberse a la capacidad institucional o a una guarda; no se resuelve contratando un plan.

<a id="cap_18"></a>

## 17 Invitar personas y gestionar accesos

1. En **Administración**, seleccione el aula y abra **Personas**.
2. Pulse **Agregar persona**. En **Cómo agregar**, use **Invitar · la persona acepta su acceso**.
3. Complete **Correo de la persona** y **Permiso en esta aula**: Docente, Observador o Administrador. Asigne solo el permiso necesario.
4. Pulse **Crear invitación**. En **Invitación lista**, use **Copiar enlace** o comparta privadamente el QR con el destinatario.
5. Pida que acepte dentro de una hora y complete el registro Android si recibirá avisos. No se envía correo automáticamente.

![Personas e invitaciones en una prueba controlada. Los correos de ejemplo no son credenciales para ingresar.](manual-usuario/capturas/13-1440-personas.png)

*Personas e invitaciones en una prueba controlada. Los correos de ejemplo no son credenciales para ingresar.*

No publique ni proyecte una invitación: el enlace es una credencial de alta y solo se muestra al generarlo. La persona nueva define su contraseña; una cuenta existente mantiene la suya. También puede usar **Vincular una cuenta existente**, indicar correo y rol y pulsar **Agregar al aula**.

Para cambiar permisos use **Editar acceso** y **Guardar acceso**. **Retirar acceso** retira la membresía de esa aula; conserva la cuenta e historial. La lista protege al propietario y a la cuenta actual frente a ciertas modificaciones. Revise antes el destinatario y el aula.

En **Invitaciones**, actualice la lista y use **Revocar invitación** sobre una pendiente si ya no corresponde. Revocar una invitación y retirar una membresía aceptada son acciones distintas. Hay límites preventivos: 10 lugares por aula incluyendo invitaciones vigentes y 10 invitaciones globales por 24 horas. Si se alcanza un límite, revise el uso y comuníquese con el responsable.

<a id="cap_19"></a>

## 18 Administrar las PC del aula

En **Administración → PC del aula** se administran los equipos que envían mediciones. No agregue aquí los celulares: cada persona registra su teléfono desde Ajustes de Android.

1. Seleccione el aula correcta y abra **PC del aula**.
2. Revise nombre, vínculo, estado y último contacto de cada PC. **PC vinculada** no demuestra por sí solo que el Arduino esté leyendo en ese instante.
3. En la PC que tendrá la placa, use **Conectar Arduino en esta PC** y siga la asignación automática del capítulo 19.
4. Para retirar una PC que ya no debe enviar datos, pulse **Retirar PC**, lea el contexto, indique el motivo solicitado y confirme.
5. Actualice la configuración y compruebe **Acceso retirado**. El historial anterior se conserva; la credencial de ese receptor deja de estar autorizada.

![Gestión de PC en una prueba controlada. El vínculo de receptor es diferente al registro de un teléfono.](manual-usuario/capturas/14-1440-pc.png)

*Gestión de PC en una prueba controlada. El vínculo de receptor es diferente al registro de un teléfono.*

Se permiten hasta dos PC activas por aula. Antes de añadir otra, identifique las existentes; no retire una instalación ajena para liberar un lugar sin saber para qué se usa.

La ruta avanzada **Registrar PC con Arduino → Nombre de la PC → Crear vínculo de PC → Descargar configuración PC** genera configuración privada. Su manejo corresponde al responsable técnico y se utiliza únicamente en la PC prevista. No la envíe por un grupo ni la copie a Android. Para el primer uso común, prefiera la asignación automática y evite manipular archivos de secretos.

<a id="cap_20"></a>

## 19 Asignar esta PC y conectar Arduino

Debe realizarse desde el portal local abierto por el panel en la PC físicamente conectada a la maqueta. El portal público orienta al panel instalado; no controla su USB directamente.

1. Conecte el Arduino con un cable USB de datos y cierre el Monitor Serie del IDE.
2. Abra el panel, **Abrir SFA Aire**, ingrese como administrador y seleccione el aula.
3. Abra **Conexión Arduino**. Si aún no está asignada, pulse **Usar esta PC para esta aula** y espere confirmación.
4. Pulse **Refrescar puertos**. En **Puerto COM**, elija la placa USB correcta; no copie COM7 del ejemplo, su número puede ser otro.
5. Pulse **Conectar Arduino**. El receptor usa 115200 baudios y solicita MONITOR al firmware.
6. Compruebe **Datos recibidos en esta PC**, antigüedad, origen y estado de nube. Confirme después las muestras en Mis aulas y Android.

![Primera asignación en prueba de interfaz. No acredita una placa física conectada.](manual-usuario/capturas/15-1440-primera-asignacion.png)

*Primera asignación en prueba de interfaz. No acredita una placa física conectada.*

**Puerto abierto** no equivale a lectura válida. Use **Comprobar conexión** si necesita verificar. **Detener lectura** envía PARAR y detiene la adquisición. Si solo aparecen puertos Bluetooth, todavía no se detectó la placa USB.

Cambiar el selector de aula no reasigna la PC automáticamente. El cambio exige administrar origen y destino, detener lectura o prueba y sincronizar los paquetes pendientes. La asignación conserva historial: los avisos anteriores no se trasladan al aula nueva.

<a id="cap_21"></a>

## 20 Preparar la maqueta y verificar sus conexiones

Este capítulo permite reconocer el montaje previsto. El responsable técnico debe confirmar la placa, el módulo, la alimentación y el firmware antes de conectar o cambiar cables. Haga modificaciones con el equipo desconectado de la alimentación.

| Componente | Conexión de esta versión |
| --- | --- |
| DHT DATA | Arduino D2. DHT22 por defecto; DHT11 requiere variante de firmware. |
| DHT VCC y GND | Alimentación admitida por el módulo y GND común. Un DHT sin placa puede necesitar pull-up. |
| MQ135 AO | Arduino A0. Verifique que su tensión esté dentro del rango admitido. |
| MQ135 VCC y GND | Alimentación regulada según módulo y GND común. |
| MQ135 DO | No se utiliza. |
| Arduino USB | Cable de datos hacia la PC receptora. |

El calefactor del MQ135 no se alimenta desde un pin digital. Confirme el orden serigrafiado de VCC, GND y señales; no todos los módulos tienen los pines en el mismo orden. No una en paralelo dos salidas de 5 V. Coloque el DHT separado del calor del MQ135.

Si la placa todavía no tiene firmware, el responsable debe cargar **arduino/SFA_Aire_Aulas/SFA_Aire_Aulas.ino** con el tipo DHT correcto. El portable no carga automáticamente ese programa ni cambia DHT22 a DHT11. Una compilación correcta no verifica el cableado.

La espera inicial de 180 segundos no sustituye el acondicionamiento del MQ135. Respete la ficha del módulo; la documentación del componente citado por el proyecto contempla más de 48 horas en sus condiciones de ensayo. Registre la estabilidad real antes de definir referencia.

Para aprender el recorrido use primero simulación. No genere humo, combustión ni gases peligrosos dentro del aula para probar una alerta. La validación física del montaje permanece separada de las capturas y pruebas de software de este manual.

<a id="cap_22"></a>

## 21 Configurar las reglas de la maqueta

Solo el administrador autorizado debe modificar las reglas, desde la PC asignada y con conexión verificada. Registre los valores anteriores y el motivo para poder revisar los cambios.

1. Entre en **Conexión Arduino** y despliegue **Reglas de aviso de esta maqueta**.
2. En **Referencia MQ135 (ADC)**, introduzca la referencia medida y documentada del montaje. El valor 300 del simulador no es una referencia universal.
3. Marque **Sensor MQ135 acondicionado y con referencia experimental** únicamente cuando se haya comprobado realmente.
4. Revise los niveles relativos y tiempos. Si corresponde, active **Activar avisos por temperatura** y configure sus umbrales.
5. Pulse **Guardar reglas** y espere confirmación. **Descartar cambios** recupera las reglas guardadas de la PC.

| Parámetro | Qué cambia |
| --- | --- |
| Aviso y alerta MQ135 | Comparación del ADC con su referencia; alerta debe representar el nivel superior previsto. |
| Persistencia | Tiempo de variación válida sostenida antes de confirmar el aviso. |
| Recuperación | Tiempo necesario para confirmar recuperación de lectura. No atiende el aviso. |
| Histéresis | Margen que evita alternar continuamente de estado cerca del umbral. |
| Avisos por temperatura | Habilita comparación de temperatura válida con niveles e histéresis configurados. |

Los valores de demostración incluyen aviso 1,30 ×, alerta 1,60 ×, persistencia 12 s, recuperación 20 s e histéresis relativa 0,10. No son límites sanitarios. Confirme las reglas efectivas de su instalación; no las reemplace solo por coincidir con una captura.

Si aparece un conflicto al guardar, descarte o revise los cambios y vuelva a consultar el estado. No declare que el sensor está acondicionado para eliminar un bloqueo. Un fallo DHT, saturación, pérdida de datos o falta de referencia puede impedir una confirmación válida.

<a id="cap_23"></a>

## 22 Probar una notificación desde la nube

La prueba rápida comprueba el recorrido de avisos sin Arduino ni receptor PC. Requiere una sesión administradora del aula, un teléfono registrado para esa aula y consentimiento para recibir simulaciones.

1. En Android, complete Ajustes del capítulo 15 y guarde **Incluir simulaciones**.
2. En el portal, seleccione esa misma aula y abra **Laboratorio**.
3. En **Probar la notificación del celular**, revise los teléfonos habilitados y el margen de entregas.
4. Si lo necesita, abra **Elegir valores de la prueba** y elija Temperatura, MQ135 o Ambos. Los valores son sintéticos.
5. Pulse una vez **Enviar aviso de prueba**. Observe la traza y compruebe el teléfono.
6. Abra la notificación y revise el aviso identificado como SIMULACIÓN. No lo confunda con una lectura actual del aula.

![Laboratorio 0.8.0 en DEMO. La misma vista informa que el ejemplo no envía notificaciones.](manual-usuario/capturas/16-portal-laboratorio.png)

*Laboratorio 0.8.0 en DEMO. La misma vista informa que el ejemplo no envía notificaciones.*

El resultado progresa por **Programadas**, **Aceptadas por FCM**, **Recibidas en app** y **Abiertas**. Aceptación por Firebase no garantiza recepción. Apertura no equivale a atención ni comprensión. La lectura incluida en un aviso es histórica.

Si no llega, consulte el capítulo 24 antes de repetir. Hay separación mínima entre pruebas, espera mientras existan entregas pendientes y guardas de consumo. No use envíos repetidos para intentar forzar la recepción. Este manual no ejecuta por sí mismo pruebas cloud.

<a id="cap_24"></a>

## 23 Ensayar el recorrido completo con la PC

La **Simulación completa con la PC · Avanzado** prueba adquisición sintética, reglas, persistencia y opcionalmente push. Es diferente de la prueba rápida cloud y de Explorar demostración.

1. Abra Laboratorio como administrador y despliegue la simulación completa.
2. Seleccione una PC vinculada y con contacto reciente. Compruebe la hora del diagnóstico; una respuesta antigua no acredita disponibilidad actual.
3. Elija el escenario Temperatura, MQ135 o Ambos y revise temperatura, humedad y ADC sintéticos.
4. Seleccione una duración acotada de 60, 90 o 180 segundos.
5. Si comprobará push, marque **Recorrer la entrega FCM a celulares habilitados para simulación**. Si no, el ensayo no enviará esos avisos.
6. Solo si corresponde interrumpir una adquisición en curso, autorice **Permitir detener USB para que este receptor ejecute la prueba**. No marque esa opción sin comprobar el uso del equipo.
7. Confirme que verificó Supabase Free y Firebase Spark sin facturación vinculada y pulse **Iniciar prueba acotada**.
8. Siga la traza: medición guardada, alarma confirmada y etapas de entrega. Use **Actualizar diagnóstico** para revisar bloqueos y **Detener prueba** si necesita finalizar.

Resultado esperado: el ensayo termina, la fuente deja de simular y sus registros permanecen identificados. Una lectura recuperada no elimina el aviso pendiente; atiéndalo si corresponde y vuelva a comprobar la fuente antes de continuar con Arduino.

Si la sección **Para iniciar** informa un impedimento, resuélvalo en su origen. La prueba no debe empezar con una PC sin contacto verificable ni sustituyendo USB silenciosamente. El diagnóstico del código local posterior a 0.8.0 tiene mejoras adicionales; el portable 0.8.0 publicado conserva su versión original.

Las reservas propias son 80 entregas operativas y 20 de simulación por día, sin préstamo entre ambas. Son guardas de la aplicación, no cuotas oficiales. Otras guardas pueden pausar sincronización aunque todavía quede cupo push. No cambie de plan ni desactive protecciones para terminar un ensayo.

<a id="cap_25"></a>

## 24 Resolver problemas de acceso lecturas y avisos

| Problema observado | Comprobaciones y siguiente paso |
| --- | --- |
| No puedo ingresar | Revise correo, contraseña y red. Si falta activación, complete la invitación. Sin recuperación disponible, contacte al administrador. |
| Ingreso pero no hay aulas | Compruebe que la carga terminó. Revise cuenta, aceptación y membresía con el administrador; no cree cuentas duplicadas. |
| Invitación vencida o revocada | Solicite una nueva. No comparta el enlace fallido en un grupo ni intente un registro libre. |
| No aparece Arduino | Cable USB de datos, alimentación y controlador. Refresque puertos. Los COM Bluetooth no son la placa. |
| Puerto ocupado | Cierre Monitor Serie y otras aplicaciones que usen esa placa. No cierre procesos desconocidos. |
| Puerto abierto sin lecturas | Compruebe firmware, 115200, DHT correcto y diagnóstico. Abrir el COM no prueba sensores. |
| Valores antiguos o sin datos recientes | Revise PC encendida, USB, última trama y paquetes pendientes. No interprete la última lectura como actual. |
| Falta referencia o revisar sensores | Revise montaje y acondicionamiento con el responsable. No copie un ADC de una captura. |
| No llega la notificación | Confirme aula registrada, AVISOS ACTIVOS, permiso Android, Google Play, internet y simulaciones guardadas si es ensayo. Consulte traza y cupos. |
| FCM aceptó pero no hay recibido | Aún no hay evidencia de recepción. Revise teléfono, sesión, restricciones de batería/red y permiso. No repita envíos sin diagnóstico. |
| No puedo atender | Confirme rol docente/admin, sesión, red y estado vigente. Un observador o DEMO no guarda atención. |
| Falló el guardado de una nota | Conserve el formulario, recupere red y revise si cambió el aviso. No suponga éxito por haber pulsado el botón. |

Antes de pedir ayuda, anote versión, hora, aula, pantalla, mensaje exacto y si es dato real o simulado. Puede adjuntar una captura revisada sin contraseñas, invitaciones ni información privada. El administrador puede consultar los identificadores de aviso y entrega para relacionar las etapas.

<a id="cap_26"></a>

## 25 Cerrar actualizar y proteger la instalación

Al terminar una jornada, revise los avisos pendientes y el estado de la fuente. Si necesita adquirir sensores durante la noche, la PC y el receptor deben seguir funcionando y no suspenderse. Cerrar el navegador no detiene la adquisición. Elija conscientemente si conservar o detener el monitoreo al salir del panel.

En Android, vaya a **Ajustes → Más opciones → Cerrar sesión y desvincular teléfono**. Esto separa el registro de la sesión anterior. Si informa un fallo de desvinculación, solicite revisión administrativa antes de reasignar el teléfono; no suponga que el cierre local completó el retiro remoto.

Para actualizar Android, conserve el APK oficial y use una versión compatible con la firma piloto. Después compruebe versión, acceso, aula, registro de avisos y preferencia de simulación. Borrar datos o desinstalar elimina el archivo personal; no es el primer paso de diagnóstico.

Para actualizar Windows, detenga el receptor de la carpeta que va a reemplazar y siga las instrucciones de la nueva entrega. Antes de mover una instalación usada, solicite respaldo de configuración y datos al responsable. No superponga archivos de versiones distintas ni elimine carpetas de datos como solución rápida.

| Carpeta de una instalación usada | Por qué requiere cuidado |
| --- | --- |
| data | Puede contener mediciones, base local e identidad o clave de instalación. |
| secrets | Contiene vínculos y configuraciones privadas de la PC. |
| artifacts | Puede contener datos de demostración, temporales o QR. |

Para entregar el programa a otra persona, comparta el ZIP original del release y la APK oficial. No recomprima una carpeta que ya usó. Cierre sesión antes de compartir una PC. No copie una cuenta de servicio Firebase a teléfonos ni al navegador.

Supabase Free y Firebase Spark se mantienen sin Billing. Las guardas no garantizan disponibilidad ilimitada. Un cambio de plan o eliminación de datos no forma parte de la operación normal ni del procedimiento de reparación de este manual.

<a id="cap_27"></a>

## 26 Comprobación de primera puesta en funcionamiento

Use esta lista después de instalar. Marque únicamente lo observado; si algo falta, anote el motivo y la persona que debe intervenir.

Lista de acceso y consulta

- Se identifica Windows/portal 0.8.0 y Android 0.8.2, sin confundir la APK incluida en el portable.
- La invitación fue aceptada por la persona correspondiente y permite ingresar con cuenta propia.
- El nombre del aula y el permiso son correctos; una cuenta ajena no debe ver sus datos.
- La persona reconoce origen real/simulado, antigüedad y valores no disponibles.
- Puede consultar Avisos e Historial y entiende que atender y normalizar son hechos distintos.

Lista del teléfono

- Se verificó el permiso Android y AVISOS ACTIVOS para el aula prevista.
- La preferencia de simulación quedó guardada explícitamente.
- Una prueba autorizada queda identificada, llega al teléfono y puede abrirse, con fecha registrada.
- Se revisó comportamiento con pantalla bloqueada/segundo plano, red y batería según el dispositivo.
- La persona distingue Marcar atendido de Archivar en este teléfono.

Lista de adquisición física

- Se confirmó placa, firmware, tipo DHT, pinout, alimentación y cable de datos.
- La PC quedó vinculada al aula y el puerto recibe muestras válidas.
- La referencia MQ135 corresponde al montaje acondicionado y está documentada.
- Las muestras físicas coinciden por origen y fecha entre PC, nube y Android, considerando el intervalo de sincronización.
- Al detener o desconectar se ve la pérdida de vigencia, sin declarar aire normal.

La existencia de esta lista no acredita su cumplimiento. Las evidencias previas de push real pertenecen a ensayos concretos; no sustituyen la aceptación de una nueva versión o instalación. El alta de otra persona, el montaje físico y Android 0.8.2 en A02 tienen validaciones externas pendientes en las fuentes consultadas.

Registro sugerido: fecha y hora, versión, PC/teléfono, aula, responsable, comprobaciones completadas, resultado observado y pendientes. No anote contraseñas ni enlaces privados en ese registro.

<a id="cap_28"></a>

## 27 Glosario alcance y referencias de la guía

| Término | Significado práctico |
| --- | --- |
| Aula | Contexto al que pertenecen mediciones, personas y avisos. |
| PC receptora | Equipo que recibe Arduino y sincroniza; no es un celular. |
| ADC | Número de lectura analógica del MQ135; no concentración de un gas. |
| Referencia | Valor experimental del montaje usado para comparar la señal. |
| Persistencia | Tiempo de variación sostenida necesario para confirmar un aviso. |
| Push o FCM | Entrega por internet al teléfono registrado mediante Firebase Cloud Messaging. |
| Recibido y abierto | Evidencias de llegada a app y apertura; no acreditan comprensión o acción física. |
| Atendido | Estado compartido de atención humana del aviso. |
| Archivo personal | Organización local del teléfono; no cambia la atención compartida. |
| SIMULACIÓN | Datos sintéticos; un ensayo autorizado puede generar una notificación real. |
| Cola pendiente | Trabajo guardado que todavía necesita sincronización o entrega. |

Esta edición describe la operación de la infraestructura SFA Aire ya configurada. No enseña a crear proyectos cloud nuevos, ejecutar SQL, contratar servicios, publicar código o distribuir una app con firma de producción. Esas tareas requieren documentación técnica y una identidad autorizada.

Fuentes contrastadas: README y código de pantallas del portal; docs/GUIA_PUBLICA.md; PORTAL_PUBLICO_E_INVITACIONES.md; ATENCION_SIMPLE.md; CONEXION_ARDUINO.md; HARDWARE.md; IMPLEMENTACION_UI_080.md; ANDROID_082_AVISOS_Y_BANDEJA.md; Entregas/ANDROID_ACTUAL.json. Se prefirió la versión actual sobre guías históricas que aún describen coordinación obligatoria o APK antiguas.

Las capturas web de 0.8.0 y las pantallas de invitación/administración proceden de pruebas controladas conservadas en el proyecto. Las capturas Android son nativas de 0.8.2 en emulador y DEMO. El archivo de trazabilidad adjunto identifica cada imagen. No contienen una invitación utilizable ni datos de acceso reales.

Para consultar: https://sfa-aire-aulas.web.app/remoto. Para archivos publicados: https://github.com/hfreedo/SFA-Aire-Portal/releases. Se verificaron el portal y el ZIP Windows 0.8.0; Android 0.8.2 estaba disponible localmente pero no en releases públicos al cerrar esta edición. Los enlaces temporales Wi-Fi y las invitaciones privadas no se incluyen en este manual.

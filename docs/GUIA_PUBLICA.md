# Usar SFA Aire en clase

## Descargas

Los archivos oficiales están en [Releases](https://github.com/hfreedo/SFA-Aire-Portal/releases/latest):

| Archivo | Propósito |
| --- | --- |
| `SFA_Aire_Windows_0.8.0_portable_x64.zip` | Panel y receptor autónomos para Windows 10/11 x64. Extraer toda la carpeta. |
| [SFA_Aire_0.8.0.apk](https://github.com/hfreedo/SFA-Aire-Portal/releases/tag/v0.8.0) | App Android piloto, actualización visual distribuida por separado. |
| `SHA256SUMS.txt` | Verificar la integridad de las descargas. |

No se necesita instalar Python o Node.js para usar el portable. La compilación
publicada se realiza en Windows 11 x64. Los controladores USB de la placa y el
firmware Arduino se preparan por separado.

Los ejecutables Windows no incluyen firma Authenticode. La APK conserva la firma
piloto debug descrita más abajo. Comprueba los hashes publicados para identificar
los archivos originales.

## Windows: primer uso

1. Extrae el ZIP en una carpeta de tu usuario con permiso de escritura. No ejecutes
   el panel dentro del ZIP ni mezcles archivos con una instalación anterior.
2. Abre `Panel SFA Aire.exe` y pulsa **Abrir SFA Aire**: inicia el servidor automáticamente.
   **Conectar Arduino** es un acceso al mismo portal. Las herramientas inferiores
   ofrecen demostración sin nube e instalación Android por Wi-Fi.
   **Detener monitoreo** detiene el servidor y la demostración de esta carpeta.
   Al salir, elige conservar el monitoreo o detenerlo antes de cerrar el panel.
3. Para monitoreo real, abre el sistema e inicia sesión con tu cuenta autorizada.
4. Selecciona el aula, entra a **Conexión Arduino** y pulsa **Usar esta PC para esta aula**.
   La cuenta debe ser administradora; el servidor crea un vínculo exclusivo de esa PC.
   Si el aula ya tiene dos PC activas, el administrador debe revisar cuáles conserva.
5. Refresca los puertos COM, selecciona el Arduino y conecta. Revisa la referencia
   MQ135 y los umbrales del aula antes de interpretar los resultados.

El receptor escucha por defecto sólo en `127.0.0.1`. El portal público puede
consultarse desde internet, pero el USB se controla desde el panel de la PC.
No se abren puertos del router ni se cambian reglas de firewall automáticamente.

La primera vinculación necesita internet. El detalle local se conserva en SQLite;
la sincronización utiliza una cola durable y guardas de consumo. Estar sin red no
equivale a que el teléfono haya recibido un aviso.

Esta entrega Windows 0.8.0 incluye la APK piloto 0.8.0. La APK también se puede descargar por separado desde
su release; el ZIP Windows ya publicado conserva su contenido original. El nuevo panel utiliza el ícono oficial en el ejecutable y la ventana.

## Maqueta

Arduino UNO/Nano AVR, DHT22 por defecto en D2 y MQ135 AO en A0, con GND común.
El DHT11 requiere seleccionar la variante correspondiente en el firmware.
Comunicación a 115200 baudios: `MONITOR` inicia lecturas y `PARAR` las detiene.

El DHT mide temperatura/humedad; el MQ135 entrega una señal ADC relativa a una
referencia experimental. La calibración y el acondicionamiento deben comprobarse
con el montaje físico. No se calcula concentración de CO₂, calidad certificada ni AQI.

## Android y cuentas

La APK requiere Android 8 o posterior; FCM necesita servicios de Google Play e
internet. Se publica como **piloto con firma debug**, compatible con las versiones
piloto anteriores que conservan esa firma; no es una release de producción firmada.

El administrador genera una invitación por correo de destinatario, aula y permiso,
y comparte privadamente el enlace o QR. El destinatario crea su contraseña si es
nuevo; una cuenta existente conserva la suya. El enlace vence en una hora y puede
revocarse. Nunca se debe proyectar un QR de invitación al grupo.

Tras ingresar en la app, registra las notificaciones desde Ajustes. Habilita la
recepción de simulaciones sólo si participarás del ensayo. La confirmación de FCM,
la recepción en Android y la apertura son hechos distintos.

## Privacidad al mover el portable

El ZIP original no contiene sesiones, datos de personas, mediciones ni claves
privadas. Incluye únicamente la URL y la clave pública del cliente Supabase,
necesarias para mostrar el acceso; esas claves no conceden permisos administrativos.

Después de usarlo se crean archivos privados:

- `data/`: base SQLite, identidad de instalación, clave de acceso local y registros.
- `secrets/`: vínculo privado de la PC y configuraciones pendientes propias.
- `artifacts/`: datos aislados de demostración y archivos temporales/QR.

**Para entregar el sistema a otra persona, comparte el ZIP original del release.**
No vuelvas a comprimir la carpeta que ya utilizaste. Cierra sesión en el navegador
antes de compartir la PC. Eliminar un vínculo local no retira automáticamente el
registro cloud: esa gestión corresponde al administrador del aula.

El portable no hereda variables de credenciales Firebase ni directorios de datos
de otras instalaciones al iniciar sus componentes. No incluye cuenta de servicio
Firebase, token de administrador Supabase ni la credencial del aula del desarrollador.

## Validación

La entrega distingue pruebas de software y prueba física:

- Suite Python de lógica, API, aislamiento y permisos, incluyendo primera vinculación.
- RPC de primera PC comprobada localmente con rechazo de anónimos, roles ajenos,
  suplantación de origen, duplicados y límite de dos PC. En Supabase se comprobó
  el permiso, la idempotencia y el secreto mediante una transacción revertida.
- Builds web local/Hosting y APK; revisión visual del portal en escritorio y móvil.
- Portable validado después de extraer el ZIP limpio, sin usar Python/Node externos,
  con arranque/detención del receptor, configuración pública, demo aislada e integridad.
- Escaneo de valores privados, contenido APK/ZIP y hashes SHA-256.

El informe público del release identifica el resultado de la validación del ZIP.
La prueba física del montaje, la aceptación de una invitación por otra persona y
la ejecución de la APK 0.8.0 en el Samsung permanecen pendientes. Las pruebas de
transporte simulado no se presentan como envíos FCM reales.

Se conservan Supabase Free y Firebase Spark. No se vincula Billing ni se activan
servicios pagos. Sus cuotas pueden limitar el servicio; el proyecto no promete
disponibilidad ilimitada.

## Desarrollo y terceros

El repositorio incluye fuentes del portal, receptor local, firmware y app Android. Para modificar
la interfaz: `npm ci` y `npm run build` en `interfaz_web`. El build público usa
`npm run build -- --mode hosting`. La reproducción del portable se documenta en
`herramientas/compilar_portable.ps1`; requiere Python 3.13 x64, las dependencias
declaradas y PyInstaller. No se guardan secretos en el código.

Las migraciones locales y el proyecto cloud existente usan identificadores de
historial diferentes. En un proyecto ya configurado, revisa y reconcilia ese
historial antes de ejecutar una sincronización automática de migraciones.

Para reproducir el portable desde estas fuentes:

1. Crea `.venv` con Python 3.13 x64 e instala `servidor_pc/requirements.txt`
   y `herramientas/requirements-panel.txt` dentro de ese entorno.
2. Construye `interfaz_web` con `npm ci` y `npm run build`.
3. Descarga la APK 0.8.0 del release v0.8.0 en `Entregas/`. Su versión y hash se verifican
   con `docs/ANDROID_PILOTO_072.json`.
4. Guarda la configuración **pública** del cliente en `config/public-config.json`
   con `url` y `publishable_key`. Se puede obtener de la configuración pública del
   portal; no requiere credencial de PC ni cuenta de servicio. No uses service_role.
5. Ejecuta `herramientas/compilar_portable.ps1` y luego el verificador del ZIP.

Para compilar Android con notificaciones de tu propio proyecto Firebase, coloca su
`google-services.json` en `android_app/app/` y la configuración pública de Supabase
en `android_app/app/src/main/assets/sfa-public.json`. Ambos archivos son locales a
la instalación; las cuentas de servicio y las claves privadas nunca van en la app.

Las dependencias conservan sus licencias. El ZIP incluye `THIRD_PARTY_NOTICES.md`
y los avisos/licencias recopilados del runtime en `licenses/`.

> Actualización de desarrollo, 26/10/2026: la próxima entrega usa **Avisos → Marcar
> atendido**, con nota opcional. Compartir por otro canal es opcional y no hay
> coordinación ni indicaciones obligatorias. [Detalle y estado](ATENCION_SIMPLE.md).
> La guía siguiente documenta la entrega histórica 0.6.2, aún distribuida.

# SFA Aire v0.6.2 — guía vigente

## En esta PC

Abra **Panel SFA Aire.exe** (o `abrir_panel.bat`) para elegir monitoreo remoto,
receptor Arduino/USB, demostración sin nube o descarga Android por Wi-Fi.
El panel utiliza esta instalación: conserve el ejecutable junto a la carpeta del
proyecto y su entorno preparado. La opción Wi-Fi comparte solo la APK durante
30 minutos; celular y PC deben estar en la misma red.

Abra `iniciar_portal_remoto.bat`. Ingrese con la cuenta institucional asignada.
La conexión pública se completa automáticamente desde el receptor configurado;
los detalles técnicos quedan dentro de «Conexión del proyecto».

- **Mis aulas:** fuente, lectura, antigüedad y atención pendiente. SIMULACIÓN
  identifica datos sintéticos; «Sin datos recientes» impide tomarlos como actuales.
- **Incidentes:** historial de atención. Una lectura normal no cierra un incidente.
- **Coordinación:** responsable vigente, indicación, comprensión, impedimento,
  resultado y cierre humano. Requiere identidades y responsabilidades asignadas.
- **Laboratorio:** solo administradores; pruebas acotadas y con consentimiento
  de los teléfonos. Revise el cupo antes de iniciar. No repetir para «hacer llegar»
  un mensaje ya recibido: primero consulte su traza.

En Incidentes, use los filtros para elegir pendientes o resueltos. «Atender» abre
un formulario de observación; «Resolver» solicita comprobación y motivo. Si el
servidor rechaza la acción, la nota se conserva. Cancelar no guarda cambios.

Para el receptor USB abra `iniciar_pc.bat` y elija Conexiones. Una segunda apertura reutiliza el receptor existente cuando corresponde a esta instalación. Cierre el Monitor Serie del IDE antes de conectar.
El firmware usa 115200, DHT DATA D2, MQ135 AO A0 y GND común. Revise HARDWARE.md.

## Samsung A02 y otros Android

La APK v0.6.2 abre el monitoreo remoto. Inicie sesión; no contiene una cuenta ni
contraseña. **Mi aula** muestra lecturas; **Incidentes** concentra la respuesta;
**Ajustes** permite registrar avisos, consentir simulación, revisar permisos y salir.
La conexión LAN está dentro de Ajustes → Conexión local avanzada.

Instale la APK desde el ZIP o por transferencia propia. USB no es obligatorio.
La nueva APK debe probarse en el A02 antes de iniciar el piloto; la recepción y
apertura real ya demostradas corresponden a la v0.6. El emulador valida interfaz
y ejecución con datos de ejemplo, no recepción FCM física en la nueva versión.

Al cerrar sesión use «Cerrar sesión y desvincular este teléfono». Si informa
fallo de desvinculación, el administrador debe revisar el registro antes de
reasignar el celular. Cada persona usa su cuenta; no se comparte una sesión.

## En otra PC: paquete de fuentes

Instale Python y Node compatibles (Python 3.13 y Node 24 fueron usados), extraiga
el ZIP completo y ejecute `preparar_entorno.bat`. Luego abra el portal. La carpeta
de entrega no incluye secretos, cuentas, sesión ni base de datos privada.
Sin vínculo propio de receptor, la PC sirve para demostración local; el receptor
cloud necesita una credencial limitada del mismo proyecto, asignada por su administrador.

No regenere Firebase/Supabase para esta instalación ya activada. Para instalar
una infraestructura nueva, aplique las seis migraciones en orden y configure
credenciales propias. La cuenta de servicio cloud reside en Vault; no se copia
a Android/web. `secrets/firebase-admin.json` solo corresponde al emisor LAN opcional.

## Si algo falla

1. Lectura vencida: revisar receptor, COM, cable y última sincronización. No
   presentar el último valor guardado como una lectura actual.
2. Aviso ausente: revisar traza (encolado/FCM/recibido/abierto), permisos Android,
   registro del teléfono, consentimiento de simulación y reservas 80/20.
3. Sesión o red: volver a actualizar; las acciones se bloquean sin estado verificable.
4. Incidente sin responsable: usar el canal institucional alternativo y asignar
   personas reales antes del piloto. No cerrar mediante SQL para simular atención.

No cambiar planes, vincular Billing o desactivar guardas para resolver una falla.
El sistema es un prototipo de observación relativa, no un instrumento sanitario certificado.


## Puerto ocupado por otra copia de SFA Aire

El panel actualizado reutiliza el receptor de su propia carpeta. Si otra copia
usa el puerto habitual, elige uno disponible y recuerda la dirección de esta
instalación. No cierra procesos ajenos ni mezcla datos entre carpetas. Abra
el monitoreo desde Panel SFA Aire.exe o iniciar_portal_remoto.bat para obtener
la dirección correcta; no es necesario liberar manualmente el puerto 8766.

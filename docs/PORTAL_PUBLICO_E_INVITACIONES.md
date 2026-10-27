# Portal público e invitaciones · 26/10/2026

Portal: https://sfa-aire-aulas.web.app/remoto

## Recorrido

1. Administrador: Administración → aula → Personas → Agregar persona.
2. Indicar correo y permiso; Crear invitación. Copiar enlace o mostrar QR.
3. Compartir de forma privada con la persona indicada. El enlace es una credencial: no publicarlo ni proyectarlo al grupo.
4. La persona abre el enlace y crea su contraseña. Si ya tiene cuenta, utiliza su contraseña actual.
5. El aula se asigna al aceptar. Después puede ingresar en web o Android con la misma cuenta.
6. En Android, registrar las notificaciones y su preferencia de simulación desde Ajustes. Aceptar una invitación no concede permisos de notificación del sistema operativo ni registra un token FCM automáticamente.

«Tengo una invitación» permite pegar el enlace completo en web. Android 0.7.2 abre esa pantalla en el navegador del celular; después se inicia sesión en la app. No se implementó transferencia automática de sesión navegador/app.

## Alcance público y local

Firebase Hosting sirve archivos estáticos y conexión pública Supabase. No contiene claves administrativas ni credenciales de PC. Las RPC verifican cuenta y aula. El portal público utiliza los mismos datos y reglas de acceso del portal local.

La adquisición USB/COM necesita el panel instalado en la PC del Arduino. El portal público muestra instrucciones y un enlace al panel local; nunca hace solicitudes `/api/workspace/local` al dominio público. El laboratorio mantiene autorización admin en RPC y sus límites vigentes.

GitHub conserva una copia pública del código del portal y del backend cloud. No se usa GitHub Pages para el formulario de acceso. Las fuentes del receptor PC y del firmware acompañan al portal. La APK y el portable Windows se distribuyen como archivos de Releases; no se publican claves, bases, registros ni capturas de personas.

## Seguridad y consumo

- Invitación ligada al correo, aula y rol, con secreto aleatorio de 256 bits. Solo su hash SHA-256 se almacena en el esquema privado.
- Enlace válido por una hora, revocable; aceptación atómica. Repetir una aceptación ya completada por la misma cuenta no duplica miembros ni restaura accesos retirados.
- Crear/listar/revocar requiere admin del aula. Al aceptar se vuelve a comprobar que el creador conserva administración. La invitación no reemplaza el permiso de una persona ya asignada.
- Cuentas existentes: no se generan enlaces de recuperación ni se cambia su contraseña. Cuentas nuevas: Supabase Auth verifica el token de alta y establece la contraseña; el administrador no la conoce.
- El registro libre está deshabilitado en Supabase; se conserva la confirmación de correo de Auth. El enlace privado generado con `generateLink(type: invite)` actúa como credencial de alta; su entrega manual no acredita por separado control del buzón.
- Revocar bloquea la incorporación al aula. No elimina una cuenta Auth que ya se haya preparado ni invalida por sí solo una sesión Auth. Sin membresía esa cuenta no accede a mediciones.
- Diez invitaciones globales por 24 horas; diez lugares por aula contando pendientes vigentes; guarda conservadora de cincuenta cuentas. La guarda de reservas puede limitar altas antes de cincuenta cuentas efectivas. Historial de invitaciones acotado a treinta días y treinta filas por consulta.
- Enlaces en fragmento, retirados del historial visible al abrir; recuperación temporal en `sessionStorage`, eliminada al aceptar o volver al acceso. Sin analítica, servicios de QR externos ni registro de tokens en consola.
- Spark y Free conservados. No se habilita Billing, Functions de Firebase, App Hosting, Storage ni servicios de correo pagos. El build de Hosting se limita a 5 MB; activos con hash se cachean, configuración pública no se cachea. Las cuotas de transferencia del proveedor pueden suspender el sitio; no se promete disponibilidad ilimitada.

## Correo

Esta entrega genera enlace/QR; **no envía un correo automáticamente**. El mensaje lo dice explícitamente. Para correo automático se necesita configurar y validar un proveedor SMTP propio y sus límites; el SMTP predeterminado de Supabase no es una solución general para invitar direcciones externas. No se contrató ningún servicio.

## Compilar y desplegar

En `interfaz_web`: `npm ci`, `npm run build` y `npm run build -- --mode hosting`.
En la raíz: `.venv/Scripts/python.exe herramientas/preparar_portal_publico.py`.
Este paso lee únicamente `secrets/supabase-public.json` y valida que la clave sea pública.

`firebase deploy --only hosting --project sfa-aire-aulas` con una identidad autorizada. Como alternativa para la cuenta de servicio existente, `herramientas/publicar_firebase_hosting.py` sigue la API REST oficial. El CLI de esta PC fue rechazado por su comprobación de Service Usage; la API de Hosting sí autorizó el despliegue. No se ampliaron permisos IAM ni se habilitaron APIs adicionales.

Supabase: migración `20261027015219_classroom_invitations.sql` y función `aire-invitations`; JWT obligatorio en el cliente, validado explícitamente con Auth getUser y autorización admin en RPC. La comprobación JWT legada del gateway se deshabilita, como en aire-members, por las sesiones ES256 del proyecto; no se admiten solicitudes anónimas. Configuración reproducible en supabase/config.toml.

## Evidencia y límites

Comprobados: 96 pruebas Python; SQL de invitaciones y administración en PostgreSQL local PGlite; Edge con transporte controlado; recorrido web alta/cuenta existente, error/reintento, QR y revocación a 1440/390/320; builds local/Hosting y Android `assembleDebug`.

Estas pruebas de aceptación usan Auth controlado; no equivalen a que una nueva persona haya completado el alta real. Pendiente un ensayo humano del enlace con una cuenta nueva y de Android 0.7.2 en el Samsung. No se generaron alertas ni envíos FCM reales para validar esta mejora.

Referencias: https://firebase.google.com/docs/hosting/api-deploy · https://firebase.google.com/docs/hosting/usage-quotas-pricing · https://supabase.com/docs/reference/javascript/auth-admin-generatelink · https://supabase.com/docs/guides/auth/auth-smtp

## Refinamiento del portal online

Ayuda Arduino: enlace y aclaración separados en bloques con espacio vertical. Acceso con altura ajustada al contenido, sin mínimo de pantalla completa más márgenes en escritorio. Fallos de carga inicial: una tarjeta de recuperación sustituye los indicadores sin verificar; no se afirman cero aulas ni ausencia de avisos. Se conservan los datos previos cuando sí existía una consulta verificada. Revisión y capturas a 1440, 1280, 750, 390 y 320 píxeles.

Repositorio cambiado a público por solicitud expresa. Se revisó todo su historial de archivos antes de cambiar visibilidad; la publicación del código no concede acceso a aulas ni a cuentas.

# SFA Aire · Portal de aulas

Portal: https://sfa-aire-aulas.web.app/remoto

Código del portal React y backend Supabase del proyecto educativo independiente SFA Aire.
Esta exportación conserva el portal y las migraciones/Edge Functions. El receptor PC,
el firmware Arduino y la app Android permanecen en el proyecto principal.

Acceso por cuenta y aula; invitaciones por enlace privado/QR y contraseña propia.
No incluye secretos, sesiones, datos de mediciones ni cuentas de personas.
Firebase Hosting Spark y Supabase Free; sin facturación vinculada por este despliegue.

## Desarrollo

En `interfaz_web`: `npm ci` y `npm run build -- --mode hosting`.
Para preparar Hosting, proporcionar localmente `secrets/supabase-public.json`
con `url` y `key` pública anon/publishable. Nunca usar service_role.
Ejecutar `python herramientas/preparar_portal_publico.py`.
La publicación requiere una identidad propia autorizada en Firebase.

Para comprobar SQL local: `npm ci --prefix herramientas/sql-check` y
`node herramientas/sql-check/invitations.test.mjs`.
Las Edge Functions requieren secretos gestionados por Supabase; no están en Git.

Alcance, seguridad, correo y pruebas: [documentación](docs/PORTAL_PUBLICO_E_INVITACIONES.md).

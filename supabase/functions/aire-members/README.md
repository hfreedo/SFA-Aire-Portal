# aire-members

Administración de cuentas por aula. La cuenta debe autenticarse con Supabase Auth
(/auth/v1/user) y ser administradora del aula mediante aire_classroom_admin antes
de cualquier operación privilegiada. El rol vuelve a verificarse al asignar acceso.

Desplegar con verify_jwt=false: esta función realiza autenticación propia con Auth,
compatible con los formatos actuales de JWT. Esto no habilita acceso anónimo:
sin sesión o con JWT inválido responde 401; sin administración del aula, 403.
Las claves de servicio solo provienen del entorno protegido de Edge Functions.

No envía correos. Una cuenta nueva recibe la contraseña inicial escrita por el
administrador. Las cuentas existentes conservan su contraseña. No se registran ni
se devuelven contraseñas o tokens. Si la creación tiene éxito pero cambia el permiso
antes de asignar, conserva la cuenta e informa que debe vincularse; no la borra.

Guardas: 8 KiB por formulario, 10 personas por aula y 50 cuentas totales para
creación. Estas últimas son guardas propias; no cifras de cuota del proveedor.

Referencias: [Auth Admin createUser](https://supabase.com/docs/reference/javascript/auth-admin-createuser) y [autenticación de funciones](https://supabase.com/docs/guides/functions/auth).

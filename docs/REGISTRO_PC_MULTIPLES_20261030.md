# Registro de PC para pruebas en varios equipos

Corrección del 30/10/2026. Se amplió de 2 a 10 PC habilitadas por aula,
con un único valor compartido entre alta inicial, asignación, alta manual y
capacidades administrativas. El registro no exige retirar otra PC ni que
las demás estén encendidas. Diez es una guarda propia del proyecto, no una
restricción de Supabase.

## En cada computadora nueva

1. Extraiga el portable en una carpeta propia, con permiso de escritura.
2. Abra **Panel SFA Aire.exe** y entre con una cuenta administradora del aula.
3. En **Conexión Arduino**, elija el aula y pulse **Usar esta PC para esta aula**.
4. Elija el puerto USB/COM y pulse **Conectar Arduino**.

El alta se realiza una sola vez por instalación. Abrir el portal para consultar
o registrar un celular en Android no crea otra PC. **Crear vínculo manual
(avanzado)** se conserva para configuraciones técnicas; no forma parte del
recorrido habitual. Administración actualiza los registros al volver a entrar.

No copie las carpetas `data` ni `secrets` de una PC ya configurada a otra.
Use el ZIP limpio: cada instalación genera su propia identidad y credencial.
Para cambiar de aula, detenga la lectura y espere la sincronización de los
datos pendientes; esta protección evita mezclar mediciones entre aulas.

## Cuando el acceso de una PC fue retirado

La pantalla muestra **Acceso de esta PC retirado** y permite al administrador
**Volver a registrar esta PC**. Se crea un vínculo nuevo, con otro secreto;
la credencial retirada sigue invalidada y el historial conserva su origen.
Un reintento tras perder la respuesta reutiliza el borrador privado y no
duplica registros. No se recupera el acceso automáticamente sin sesión admin.

## Consumo y permisos

Se mantienen las cuotas globales de mediciones, pruebas, envíos y almacenamiento,
sin vincular facturación. El número de PC registradas no es el consumo de datos:
varias PC enviando simultáneamente comparten esas mismas cuotas.
El error de almacenamiento se distingue del límite de PC; retirar una PC no
elimina ni libera su historial. Las RPC conservan autorización admin del aula.

## Evidencia

- 134 pruebas Python aprobadas, incluyendo recuperación, reintento privado y
  rechazo a usuarios sin rol o lectura activa.
- 37 comprobaciones SQL específicas: cuatro identidades independientes, dos
  aulas, regreso sin duplicados, límite 10 y credenciales retiradas inválidas.
- Ciclo de vida: 38; asignación: 15; recorrido cloud: 42; independencia: 11.
  Los transportes de estas pruebas son locales/simulados; no acreditan FCM real.
- Build web aprobado y revisión del portal local. Migración aplicada en Supabase.
- Recuperación comprobada desde la sesión administradora real del navegador:
  esta PC volvió a quedar asignada a Aula 3ro. BTI. El escaneo mostró solo
  Bluetooth; no se comprobó una conexión Arduino física en esta revisión.

Artefacto: `Entregas/SFA_Aire_Windows_multipc_20261030_portable_x64.zip`.
Contiene el receptor actualizado y la APK 0.8.0 original del portable; la APK
0.8.2 sigue siendo una entrega separada. No se modifica Android en esta corrección.
La instalación en las otras computadoras físicas requiere su propio ensayo.

El ZIP exacto se extrajo en una carpeta limpia y se inició su ejecutable en
el puerto temporal 8896: salud correcta, portal HTTP 200, configuración pública
disponible y ninguna credencial privada de PC preexistente. Después se detuvo
ese servidor. SHA-256 y resultado en
`artifacts/multi-pc-portable-clean-report.json`. El paquete pasó la auditoría
de exclusión de datos privados del empaquetador.

El portal alojado no se redeplegó en esta revisión; la cuota cloud nueva sí
está aplicada y es compatible con los clientes anteriores.

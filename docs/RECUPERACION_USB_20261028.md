# Recuperación USB y actualización detenida — 28/10/2026

## Hallazgo

El servicio ejecutado conservaba la misma muestra durante tres consultas separadas por dos segundos: antigüedad aproximada 1880–1885 s, source=arduino, serial=error y Conexión serie interrumpida. El tiempo de consulta era 5–14 ms. Por tanto, el dato antiguo no se debía entonces a la frecuencia de refresco visual: no entraban muestras nuevas.

El lector anterior cerraba el puerto al interrumpirse y no intentaba recuperarlo. Además, un error de close() dentro del manejador de fallos podía escapar y finalizar la tarea de adquisición.

## Corrección

- Guarda en memoria el COM elegido y su VID/PID/número de serie disponible mientras la fuente Arduino esté activa.
- Tras una interrupción, reintenta ese mismo COM cada cinco segundos. No explora/conecta otro puerto ni acepta hardware de identificadores distintos. CH340 sin número de serie no permite distinguir dos placas con idéntico VID/PID: la comprobación no equivale a una identidad física única.
- Recupera MONITOR si se perdió por el arranque/reinicio de UNO; no fabrica una muestra ni actualiza su fecha por abrir el puerto.
- Detener lectura o cambiar de fuente cancela la recuperación. Reiniciar todo el servicio sigue requiriendo conectar desde la interfaz.
- Conserva fragmentos seriales entre timeouts; una trama inválida no impide procesar la siguiente válida. Los errores de cierre quedan contenidos.
- La pantalla distingue Recuperando conexión USB y conserva el COM configurado mientras espera.

## Validación y aplicación

111 pruebas Python correctas, incluidas seis nuevas de recuperación; seis pruebas de presentación local correctas. npm run build correcto. Ejecutable receptor reconstruido y aplicado localmente, respaldado en artifacts/serial-recovery-backup. No se cambió firmware, base de datos, credencial, cuota cloud ni APK. No se publicaron releases ni Hosting.

Al intentar la verificación física final, Windows dejó de enumerar COM7: sólo COM5/COM8 Bluetooth. La API rechazó la conexión como Puerto no disponible; no se sustituyó por otro COM. Se solicitó al usuario reconectar el UNO. La recuperación ante desconexión está validada con transporte serial simulado; no atribuirle una prueba física de desenchufar/reconectar hasta completar ese ensayo.

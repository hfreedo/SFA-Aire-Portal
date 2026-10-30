# Arduino real: DHT11 y actualización local — 28/10/2026

## Causas y cambios aplicados

- El sketch seleccionaba DHT22; la maqueta conectada usa DHT11. Se cambió el valor predeterminado a DHT11 y se cargó en Arduino UNO, COM7. DHT22 sigue disponible cambiando DHT_TYPE antes de compilar/cargar.
- La biblioteca instalada es DHT sensor library de Adafruit 1.4.7, con Adafruit Unified Sensor 1.1.15. Su implementación soporta ambos sensores y reutiliza lecturas durante dos segundos. No se reemplazó ni modificó la biblioteca.
- Firmware: muestras cada dos segundos, sin cambiar campos JSON, pines ni comandos MONITOR/PARAR/LEER. La ausencia o fallo del DHT mantiene temperatura/humedad null y no descarta MQ135.
- Portal: consulta local cada segundo, sin consultas solapadas. Conserva el componente, el puerto, el despliegue de reglas y los cambios no guardados al navegar dentro de la misma sesión/aula. Cambiar sesión/aula reinicia ese contexto. Mientras la sección está oculta no consulta.
- Receptor: consultas de estado/puertos/asignación ya no esperan config_lock durante solicitudes de sincronización cloud. Mutaciones mantienen su bloqueo, permisos por aula y comprobación de asignación al capturar el estado.
- Se reconstruyó SFA_Aire_Receptor.exe, se respaldó el anterior en artifacts/arduino-hotfix-backup y se reinició ordenadamente el servicio local en 8767. No se cambió la cuenta, el vínculo ni la base de datos. No se publicó un release ni se reemplazó un ZIP público.

## Verificación

- npm run build: correcto.
- Python: 105 pruebas correctas, incluidas consulta local mientras la red mantiene config_lock y conservación de MQ135 sin DHT.
- UNO: 6378 bytes flash, 290 bytes RAM; carga en COM7 correcta.
- Prueba serial física independiente: seis muestras válidas de DHT, separadas aproximadamente 2,0 s. Inicial 24,1 °C/53 %, siguientes 21,4 °C/52 %. MQ135 6 ADC. Evidencia: artifacts/arduino-dht11-physical-20261028.json.
- Servicio actualizado: después del reinicio de placa, seis respuestas con DHT válido; consultas de estado entre 5 y 10 ms. Valores observados 21,4–23,0 °C, 52–59 %, MQ135 6–7 ADC. Evidencia: artifacts/arduino-dht11-service-20261028.json. Lecturas posteriores verificadas en el portal: 22,2 °C, 54 %, 6 ADC.
- Navegador interno autenticado: Conexión Arduino → Mis aulas → Conexión Arduino conserva COM7 y las reglas desplegadas; conexión física activa. Se revisó también el componente con fixture aislado, sin USB ni nube; esa captura de QA no representa una medición física.

## Alcance y pendientes

El panel USB es local; Mis aulas y Android usan la última copia cloud. La nube conserva muestras normales cada 60 s y el portal remoto consulta cada 60 s; la espera total puede sumar esos intervalos y el siguiente ciclo de sincronización. Las transiciones de estado/laboratorio conservan su priorización anterior. No se modificaron guardas de consumo, cuotas, RPC, datos push ni servicios pagos.

MQ135 de 6–7 ADC es bajo: verificar AO (no DO), A0, alimentación, masa común, acondicionamiento y respuesta experimental. No se ha demostrado calibración ni se interpreta este valor como calidad del aire, CO2, AQI o ppm. La interfaz indica falta de referencia; no se inventó una referencia ni se activaron reglas.

No se probó una nueva alarma física ni recepción FCM en este ensayo; tampoco se actualizó Android. El servicio queda leyendo COM7. Reiniciar el programa sigue requiriendo iniciar la lectura mediante el control de conexión; la persistencia corregida corresponde a navegar entre secciones, no a reconectar automáticamente después de cerrar el servidor.

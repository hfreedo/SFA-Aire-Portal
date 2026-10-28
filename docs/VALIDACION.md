# Verificación vigente — v0.6.1

## Evidencia por capa

| Capa | Resultado comprobado | Límite |
| --- | --- | --- |
| Python | 43 pruebas aprobadas | Serial/HTTP/FCM sustituidos en tests; incluye configuración pública y exclusión de receptor duplicado |
| SQL base y worker | 132 + 35 comprobaciones aprobadas | PGlite; Vault/cron/transporte sustituidos donde corresponde |
| Worker Node | 7 pruebas aprobadas | OAuth/FCM/RPC simulados; no son envío real |
| Firmware UNO | Compilado: 6.378 bytes flash, 290 RAM | No valida montaje, DHT real ni referencia MQ135 |
| Web | npm run build; escritorio 1440×1000 y móvil 390×844 | DEMO, sin sesión ni cambios cloud; JS sin errores y sin desbordamiento |
| Android | assembleDebug, firma y tres pruebas JVM de respuestas RPC | APK de depuración para piloto; no publicación en tienda |
| Android visual | APK instalada y ejecutada en emulador API30 AOSP, 720×1600 | Fixture DEMO, sin GMS ni FCM real; no es el A02 |
| Datos vencidos | Web y Android muestran expiración; Android reloj real >100 s | No se cortó red física del A02 |
| Push real v0.6 | A02 recibió y abrió; confirmado por titular | Una prueba, no garantía de latencia ni comprensión |
| Independencia cloud | Evento persistido, receptor detenido, FCM y acuse, servicio restaurado y cola vacía | No se apagó Windows; no se pidió nueva apertura humana |
| Paquete limpio | Resultado en EXTRACCION_LIMPIA_v061.json | Entorno Python externo preparado; no ejecutable portable ni prueba física |

## Archivos de evidencia

- PRIMER_PUSH_CLOUD_REAL.json conserva el ensayo v0.6: veinte mediciones,
  un incidente, un intento, recibido/abierto y confirmación humana.
- INDEPENDENCIA_SERVICIO_v061.json registra la detención exclusiva del receptor,
  un despacho adicional justificado, el acuse con servicio detenido y recuperación.
- Evidencias_v061/Web: capturas de acceso, aulas, incidentes, coordinación,
  administración, laboratorio y datos vencidos; todo lo ficticio marcado DEMO.
- Evidencias_v061/Android: capturas ejecutadas de acceso y recorridos DEMO, ajuste
  de navegación y expiración de datos. No son renders ni mockups de otra app.
- CIERRE_v061_VERIFICACION.json y manifiesto ZIP reúnen las comprobaciones.

Las nuevas pantallas se compararon con la referencia visual pública de Anticaídas
sin modificarla; se conserva la identidad de Aire. Ver DISENO_Y_REVISION_V061.md.

## No comprobado / aceptación externa

Montaje físico y calibración; dos personas reales en coordinación; ejecución y
push de la APK v0.6.1 en el A02; comportamiento en segundo plano/corte de red/
permisos/cierre de sesión del teléfono. Los pasos están en DEMO_Y_PILOTO.md.
No declarar piloto escolar físico validado hasta documentarlos.

# SFA Aire

<!-- impeccable:product-schema 1 -->

## Platform

web

Este contexto raíz corresponde al portal web y recoge la verdad compartida del
producto. La aplicación Android tiene su contexto en android_app/PRODUCT.md:
usa Views en Kotlin y se verifica en emulador/dispositivo, no en un navegador.
El portal tiene su propia adaptación a escritorio y pantallas estrechas.

## Users

Docentes que consultan el ambiente del aula y reciben avisos; responsables que
administran personas, aulas y pruebas; estudiantes que presentan una maqueta
escolar y deben poder explicar su funcionamiento desde otra PC.

## Product Purpose

Recoger temperatura/humedad del DHT y señal relativa del MQ135 de una maqueta
Arduino, mostrar las mediciones y entregar avisos en PC y Android mediante FCM.
Las personas autorizadas del aula deben poder recibirlos. Compartir un aviso
con otra persona es opcional; atenderlo no exige protocolos ni instrucciones.

## Stack

Arduino UNO y USB serial; receptor Python/FastAPI y persistencia local; portal
React/TypeScript; Supabase para cuentas, permisos, mediciones y cola; Firebase
Cloud Messaging para Android. Consultar docs/ARQUITECTURA.md para los contratos.

## Operating Context

El Arduino se conecta a la PC del aula. El portal público permite consultar la
nube, pero no sustituye al proceso local que lee el USB. Un teléfono y una PC
son participantes distintos; una persona entra con su propia cuenta.
La prueba rápida de notificaciones cloud ya existe y no requiere Arduino.
El laboratorio también ofrece simulación completa con la PC.

## Capabilities and Constraints

- Proyecto escolar independiente de SFA anticaídas. No copiar sus identificadores,
  bases, secretos ni modificar ese proyecto.
- Supabase Free/Firebase Spark: conservar guardas; no vincular Billing ni sumar
  servicios pagos como parte del trabajo visual.
- Simulación siempre identificada. Separar hora de actualización de la app y
  antigüedad de la medición. Los datos vencidos son históricos.
- MQ135 ADC/relación con referencia no equivalen a CO₂, AQI ni ppm.
- Los permisos se aplican en backend/RPC; ocultar controles no autoriza acciones.
- Conservar sesiones, registro push, contratos y consumo durante una mejora UI.
- Recibir, abrir, atender un aviso y recuperar el ambiente son estados distintos.
- Este archivo recoge objetivos expresos del usuario y documentación existente;
  no establece que todos los recorridos estén ya probados.

## Brand Commitments

Nombre y logo de SFA Aire; identidad salvia/verde existente. Lenguaje humano,
técnico cuando aporta información, legible y sin burocracia. El usuario pide
consistencia, buena jerarquía y movimiento suave con un propósito reconocible.

## Evidence on Hand

docs/AUDITORIA_VISUAL_ANDROID_074.md y Branding/UX/auditoria-android-074 conservan
la revisión anterior. docs/PLAN_MEJORA_UX_SKILLS.md documenta la nueva evaluación,
la evidencia y los límites. Compilar, ejecutar en emulador y probar en Samsung
A02 son hitos diferentes. No inventar medidas, entregas FCM ni usuarios.

## Product Principles

1. Medir y avisar es el recorrido principal.
2. Hacer evidente qué aula, origen y antigüedad describen los datos.
3. Preferir controles familiares y pocas decisiones por tarea.
4. Mostrar una causa y una salida cuando una acción no esté disponible.
5. Comprobar la interfaz ejecutada y el paquete entregado.

## Accessibility & Inclusion

Conservar cuerpo legible y peso suficiente; el usuario ha señalado problemas con
letra fina. En Android usar sp, áreas táctiles de al menos 48 dp, fuente ampliada
y preferencias de movimiento del sistema. En web verificar foco, teclado,
contraste y ampliación. No depender exclusivamente del color o de hover.

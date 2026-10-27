# SFA Aire Android

<!-- impeccable:product-schema 1 -->

## Platform

android

## Stack

Kotlin y Android Views. No es una página web ni una aplicación Compose.
Controles de plataforma con estilos propios; evaluar componentes Material para
Views al consolidar el sistema visual. No afirmar conformidad Material 3 actual.

## Users

Docentes y responsables de aulas; estudiantes que presentan la maqueta escolar.
El dispositivo de referencia del usuario es Samsung A02 con Google Play.

## Product Purpose

Consultar temperatura/humedad DHT y señal MQ135 relativa del aula; recibir push
FCM y atender avisos sin protocolos obligatorios. Compartir y escribir una nota
son opciones independientes. Atender no declara normalización del ambiente.

## Capabilities and Constraints

Hereda las restricciones de ../PRODUCT.md y ../AGENTS.md. Proyecto independiente
de SFA anticaídas; nunca copiar sus datos o secretos. Conservar Supabase Free /
Firebase Spark, guardas, permisos de RPC, contratos y registro de sesión/FCM.
La simulación y la vigencia son explícitas; ADC no se convierte a CO₂/AQI/ppm.
El Arduino lo lee la PC por USB: la app consulta datos y recibe avisos.

Mi aula, Avisos y Ajustes son los destinos principales. La cobertura del registro
push entre varias aulas requiere verificación separada; cambiar aula en una
lista no debe presentarse como confirmación de un registro nuevo.

## Brand Commitments

Nombre/logo y verde/salvia como acento, superficies neutras, legibilidad y peso suficiente, composición
limpia, controles Android familiares y movimiento suave que comunique estado.
No sustituirlo por estética de controles iOS ni añadir burocracia.

## Evidence on Hand

../docs/ANDROID_081_IOT_CALMADO.md recoge el refinamiento actual.
../docs/PLAN_MEJORA_UX_SKILLS.md y ../docs/CRITERIOS_DISENO_UI.md contienen la
línea de base revisada y el plan pendiente. Las capturas en emulador no son
prueba física en A02 ni recepción real FCM. Verificar la APK ejecutada.

## Accessibility & Inclusion

Texto en sp, cuerpo legible, áreas táctiles ≥48 dp, fuente al 130 %, Back/teclado,
contraste y Eliminar animaciones. No disminuir toda la letra para ganar espacio.

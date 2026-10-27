---
colors:
  ink: "#243039"
  muted: "#52626F"
  primary: "#256D5B"
  selected: "#E5F0EB"
  canvas: "#F4F6F8"
  surface: "#FFFFFF"
  outline: "#D8E0E4"
  control-outline: "#82929D"
  simulation: "#695385"
  simulation-container: "#F0ECF7"
  warning: "#805316"
  warning-container: "#FFF4DF"
  alert: "#974330"
  alert-container: "#FAEBE5"
---
# SFA Aire Android · IoT calmado

## Design System Notes

Refinamiento 0.8.1 del sistema existente. Conserva marca, controles y recorridos.
Modo Operate: medir, reconocer un aviso y actuar sin protocolos adicionales.
Colores declarados en ui/AireUi.kt. El color identifica funciones y se acompaña
de etiquetas; no es una clasificación sanitaria de la señal MQ135.

## Color Palette

Fondo neutro frío, superficies blancas, texto carbón y apoyo gris. Verde/teal
reservado para acción principal, selección y estados positivos explícitos.
Simulación usa una etiqueta lavanda; advertencia usa ámbar; alerta, ladrillo.
No teñir toda una tarjeta de alarma ni confundir DEMO con permiso pendiente.
Temperatura: cobre; MQ135: teal; humedad: azul. Acentos locales en iconos;
los valores conservan contraste neutro. Los colores no añaden unidades ni umbrales.

## Typography

Sans del sistema; títulos 22/18 sp, cuerpo 16 sp, apoyo 14 sp, etiquetas 12 sp,
mediciones 32 sp con unidad subordinada. Evitar tipografía fina y respetar fuente
ampliada. La interfaz española usa formato es-PY para fechas y decimales;
la zona horaria sigue siendo la del dispositivo.

## Layout

Contexto de aula → estado/origen/vigencia → mediciones → ayuda secundaria.
Avisos: origen y severidad/estado explícitos → contenido → acción principal →
opciones con icono → detalles. Ajustes mantiene registro, preferencia y cuenta
como grupos. Fuente al 130 % apila sensores; no fijar alturas de texto.

## Elevation & Depth

Predominio plano. Bordes suaves para agrupar; contorno de control con contraste
propio para botones de contorno y campos. No sombra o hover en datos de consulta.

## Shapes

Tarjetas 16 dp, controles 10 dp, diálogo 20 dp, etiquetas 6 dp. Mantener áreas
interactivas de 48 dp aunque el icono visible sea pequeño.

## Components

Principal: relleno teal y texto blanco. Secundaria: blanca con contorno. Filas de
acciones: texto neutro e icono de función. Detalles: chevron y peso secundario.
Deshabilitado: texto/fondo grises por estado, sin multiplicar alfa sobre verde.
Barra inferior: iconos y etiquetas inactivos grises; selección teal e indicador.
Interruptor: geometría Android, posición/color diferenciados; guardado explícito.

Navegación y despliegues mantienen el movimiento breve de 0.8.0; no animar cada
muestra. Respetar Eliminar animaciones. Simulación y datos vencidos permanecen
visibles; atender y compartir siguen independientes.

## Do's and Don'ts

No gráficos ficticios, luces decorativas que parezcan conectividad real, CO₂/AQI
sin validación, círculos de progreso inventados ni fondos verdes para todo.
Capturar la APK ejecutada, incluyendo estados habilitados mediante fixtures
identificados; una captura DEMO deshabilitada no explica la acción principal real.

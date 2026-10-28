# Maqueta y sensores

## Materiales propuestos

Arduino UNO o Nano AVR de 5 V, módulo MQ135 con salida AO, DHT22 (supuesto
inicial; admite DHT11 cambiando la definición), cable USB de datos, protoboard,
conductores y fuente regulada adecuada al módulo calefactor. Para un DHT sin
placa puede requerirse resistencia pull-up de 4,7–10 kΩ entre DATA y VCC;
revise si el módulo ya la incorpora.

## Pinout de esta versión

| Componente | Conexión |
| --- | --- |
| MQ135 AO | Arduino A0 |
| MQ135 DO | Sin conectar; no se usa el comparador del módulo |
| MQ135 VCC | 5 V regulados según la placa adquirida |
| MQ135 GND | GND común con Arduino |
| DHT DATA | Arduino D2 |
| DHT VCC | 5 V si el módulo adquirido lo admite |
| DHT GND | GND común |
| Arduino | USB a PC para datos y alimentación de la placa |

**Confirme el orden serigrafiado de cada módulo:** no todos comparten la misma
disposición física. El calefactor del MQ135 no se alimenta desde un pin digital.
Para alimentación externa, conecte las masas y evite unir en paralelo las salidas
de 5 V de dos fuentes. Mantenga AO en el rango admisible de A0 de la placa AVR.
Una futura placa de 3,3 V requiere revisar los niveles antes de reutilizar este
montaje. Sitúe el DHT separado del calefactor del MQ135.

## Qué se observa

El MQ135 cambia su conductividad ante distintos gases/vapores; su respuesta no
identifica un gas por sí sola. Se promedian ocho conversiones ADC y se calcula
`ratio = mq_raw / referencia_ADC`. No se aplica una ecuación de ppm ni una
corrección ambiental no validada. El DHT informa temperatura y humedad cada
tres segundos para respetar el intervalo de lectura del DHT22.

Las lecturas exactamente 0 o 1023 se tratan como fallo/saturación. Esto no
detecta todos los fallos posibles: una entrada desconectada puede flotar en un
valor intermedio. Revise cableado y referencia antes de interpretar variaciones.

## Acondicionamiento y referencia

1. Identifique fabricante y módulo. El manual MQ135 de Winsen especifica un
   precalentamiento de más de 48 horas en sus condiciones de ensayo; respete
   la ficha aplicable al componente adquirido.
2. Después de cada encendido esta base bloquea evaluación durante 180 s. Ese
   temporizador es una espera inicial de demostración: **no sustituye el
   acondicionamiento ni demuestra que el sensor esté estable**.
3. Observe la señal en un entorno de referencia ventilado, sin estímulos de
   prueba, durante un período documentado. Registre temperatura/humedad,
   alimentación, duración y variabilidad. Determine una referencia estable.
4. En Reglas del aula ingrese esa referencia ADC y confirme acondicionamiento.
   La referencia real permanece separada del valor sintético 300 del simulador.
5. Compare repeticiones y ajuste los umbrales relativos. Los valores iniciales
   1,30 × y 1,60 × son de demostración, no límites de salubridad.

La regla implementada responde a aumentos del ADC. Compruebe esa dirección con
el módulo real; no suponga que otra placa o salida acondicionada responde igual.
Cambiar el sensor, su alimentación o montaje exige revisar la referencia guardada.

Para la primera prueba funcional use simulación. No use combustión, humo ni
gases peligrosos para provocar alarmas en un aula. Los ensayos físicos deben
tener un procedimiento docente de banco y ventilación apropiados.

## Parámetros iniciales

| Parámetro | Valor |
| --- | --- |
| Lectura periódica | 3 s, únicamente después de MONITOR |
| Aviso / alerta | 1,30 × / 1,60 × referencia |
| Persistencia | 12 s de mediciones válidas sostenidas |
| Recuperación | 20 s |
| Histéresis | 0,10 × |
| Lectura vencida | Más de 10 s sin muestra válida |

Un fallo de DHT, saturación, falta de referencia o calentamiento interrumpe la
ventana de confirmación. La pérdida de datos no se interpreta como aire normal.

## Fuentes técnicas consultadas

- [Manual MQ135 de Winsen](https://www.winsen-sensor.com/manual/mq135.html):
  principio, sensibilidad y acondicionamiento.
- [DHT22 de Adafruit](https://www.adafruit.com/product/385): temperatura,
  humedad y frecuencia máxima de lectura.
- [Biblioteca DHT de Adafruit](https://github.com/adafruit/DHT-sensor-library):
  tipos DHT11/DHT22 y lectura.

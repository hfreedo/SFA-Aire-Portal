/* SFA Aire Aulas v0.1 | UNO/Nano AVR | DHT + módulo MQ135
   DHT DATA D2, MQ135 AO A0, GND común, alimentación regulada 5 V.
   DHT22 por defecto; cambiar DHT_TYPE a DHT11 si ese es el componente real.
   MQ135: ADC relativo, sin ppm ni identificación de gas.
   El acondicionamiento inicial del fabricante NO se sustituye por este temporizador.
   Serie 115200, final de línea Nueva línea. Sin transmisión periódica hasta MONITOR.
*/
#include <DHT.h>
#ifndef DHT_TYPE
#define DHT_TYPE DHT22
#endif
const byte PIN_DHT = 2;
const byte PIN_MQ = A0;
const unsigned long INTERVALO_MS = 3000;
const unsigned long ESTABILIZACION_MS = 180000UL;
DHT dht(PIN_DHT, DHT_TYPE);
bool monitoreando = false;
unsigned long ultima = 0;
char comando[32];
byte posicion = 0;
bool desbordado = false;

void muestra() {
  long suma = 0;
  for (byte i = 0; i < 8; i++) suma += analogRead(PIN_MQ);
  int mq = suma / 8;
  float humedad = dht.readHumidity();
  float temperatura = dht.readTemperature();
  bool valido = !isnan(humedad) && !isnan(temperatura);
  Serial.print(F("{\"device_id\":\"aula-01\",\"mq_raw\":"));
  Serial.print(mq);
  Serial.print(F(",\"temperature\":"));
  if (valido) Serial.print(temperatura, 1); else Serial.print(F("null"));
  Serial.print(F(",\"humidity\":"));
  if (valido) Serial.print(humedad, 1); else Serial.print(F("null"));
  Serial.print(F(",\"dht_ok\":"));
  Serial.print(valido ? F("true") : F("false"));
  Serial.print(F(",\"warmed_up\":"));
  Serial.print(millis() >= ESTABILIZACION_MS ? F("true") : F("false"));
  Serial.println(F("}"));
}

void ejecutar() {
  comando[posicion] = '\0';
  if (strcmp(comando, "MONITOR") == 0) {
    monitoreando = true;
    Serial.println(F("# MONITOR activo cada 3 s. PARAR para detener."));
    muestra(); ultima = millis();
  } else if (strcmp(comando, "PARAR") == 0) {
    monitoreando = false;
    Serial.println(F("# MONITOR detenido."));
  } else if (strcmp(comando, "LEER") == 0) {
    muestra();
  } else if (strcmp(comando, "ESTADO") == 0) {
    Serial.print(F("# Monitor: ")); Serial.println(monitoreando ? F("SI") : F("NO"));
    Serial.print(F("# DHT tipo: ")); Serial.println(DHT_TYPE);
    Serial.println(F("# DHT D2 | MQ135 AO A0 | ADC 0-1023 | 115200 baudios"));
  } else if (strcmp(comando, "AYUDA") == 0) {
    Serial.println(F("# SFA Aire: LEER | MONITOR | PARAR | ESTADO | AYUDA"));
  } else if (posicion > 0) {
    Serial.println(F("# Comando desconocido. Use AYUDA."));
  }
  posicion = 0;
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  Serial.println(F("# SFA Aire v0.1. LEER | MONITOR | PARAR | ESTADO | AYUDA"));
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (!desbordado) ejecutar();
      else Serial.println(F("# Comando demasiado largo."));
      posicion = 0; desbordado = false;
    } else if (posicion < sizeof(comando) - 1 && !desbordado) {
      if (c >= 'a' && c <= 'z') c -= 32;
      comando[posicion++] = c;
    } else desbordado = true;
  }
  if (monitoreando && millis() - ultima >= INTERVALO_MS) {
    ultima = millis(); muestra();
  }
}

/* SFA Aire: simulador USB temporal, contrato serial v2.
   UNO sin sensores. NO son mediciones fisicas ni valores de calidad del aire.
   Requiere receptor actualizado para reconocer simulated=true.
   MONITOR inicia; PARAR detiene; LEER muestra; REINICIAR vuelve a 300 ADC.
   Cada 2 s: temperatura y humedad ficticias. Cada minuto: MQ +100 ADC.
   Ciclo: 300, 400, 500, 600, 700, 300... Sin delay() ni librerias de sensores.
*/
const unsigned long INTERVALO_MS = 2000UL;
const unsigned long ESCALON_MS = 60000UL;
bool monitoreando = false;
bool receptorCompatible = false;
unsigned long inicio = 0, ultima = 0;
char comando[32];
byte posicion = 0;
bool desbordado = false;

void muestra() {
  if (!receptorCompatible) {
    Serial.println(F("# SIMULACION USB v2: requiere receptor actualizado; envie SIMULACION_USB_V2."));
    return;
  }
  unsigned long transcurrido = monitoreando ? millis() - inicio : 0;
  unsigned long paso = transcurrido / ESCALON_MS;
  int mq = 300 + (paso % 5) * 100;
  float temperatura = 23.0 + ((transcurrido / 2000UL) % 10) / 10.0;
  int humedad = 50 + ((transcurrido / 4000UL) % 5);
  Serial.print(F("{\"serial_contract\":2,\"simulated\":true,\"device_id\":\"aula-01\",\"mq_raw\":"));
  Serial.print(mq);
  Serial.print(F(",\"temperature\":")); Serial.print(temperatura,1);
  Serial.print(F(",\"humidity\":")); Serial.print(humedad);
  Serial.println(F(",\"dht_ok\":true,\"warmed_up\":true}"));
}
void ejecutar() {
  comando[posicion] = '\0';
  if (!strcmp(comando,"SIMULACION_USB_V2")) {
    receptorCompatible = true;
    Serial.println(F("# Receptor v2 confirmado. Datos ficticios."));
  } else if (!strcmp(comando,"MONITOR")) {
    if (!receptorCompatible) {
      Serial.println(F("# SFA Aire SIMULACION USB v2. Receptor actualizado requerido."));
      return;
    }
    if (!monitoreando) {inicio = millis(); monitoreando = true;}
    Serial.println(F("# SIMULACION USB v2: datos ficticios cada 2 s; MQ +100 cada minuto."));
    muestra(); ultima = millis();
  } else if (!strcmp(comando,"PARAR")) {
    monitoreando = false; Serial.println(F("# SIMULACION detenida."));
  } else if (!strcmp(comando,"LEER")) {
    muestra();
  } else if (!strcmp(comando,"REINICIAR")) {
    inicio = millis(); ultima = millis();
    Serial.println(F("# SIMULACION reiniciada: MQ 300 ADC."));
    if (monitoreando) muestra();
  } else if (!strcmp(comando,"ESTADO")) {
    Serial.print(F("# SIMULACION USB v2 | Monitor: "));
    Serial.println(monitoreando ? F("SI") : F("NO"));
    Serial.println(F("# Sin sensores | 115200 | MQ 300-700 ADC, paso 100 por minuto"));
  } else if (!strcmp(comando,"AYUDA")) {
    Serial.println(F("# SIMULACION: MONITOR | PARAR | LEER | REINICIAR | ESTADO | AYUDA"));
  } else if (posicion) Serial.println(F("# Use AYUDA."));
}
void setup() {
  Serial.begin(115200);
  Serial.println(F("# SFA Aire SIMULACION USB v2. Firmware temporal sin sensores. Use MONITOR."));
}
void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (!desbordado) ejecutar();
      else Serial.println(F("# Comando demasiado largo."));
      posicion = 0; desbordado = false;
    } else if (posicion < sizeof(comando)-1 && !desbordado) {
      if (c >= 'a' && c <= 'z') c -= 32;
      comando[posicion++] = c;
    } else desbordado = true;
  }
  if (monitoreando && millis()-ultima >= INTERVALO_MS) {
    ultima = millis(); muestra();
  }
}

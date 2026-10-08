#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

const bool USE_ACCESS_POINT = true;

const char* AP_SSID = "VeloTrilho_ESP32";
const char* AP_PASS = "12345678";

const char* WIFI_SSID = "SEU_WIFI_AQUI";
const char* WIFI_PASS = "SUA_SENHA_AQUI";

const uint16_t WS_PORT = 81;
WebSocketsServer webSocket = WebSocketsServer(WS_PORT);

const int PIN_SENSOR_1 = 4;
const int PIN_SENSOR_2 = 5;
const int PIN_SENSOR_3 = 18;
const int PIN_SERVO    = 13;

Servo servoTrilho;
int currentServoAngle = 0;

const float D1 = 0.00;
const float D2 = 0.50;
const float D3 = 1.00;

volatile unsigned long t1_micros = 0;
volatile unsigned long t2_micros = 0;
volatile unsigned long t3_micros = 0;

volatile bool s1_triggered = false;
volatile bool s2_triggered = false;
volatile bool s3_triggered = false;
volatile bool run_completed = false;

const unsigned long DEBOUNCE_US = 50000;
volatile unsigned long last_trigger_time = 0;

unsigned long run_counter = 1;

void IRAM_ATTR isr_sensor_1() {
  unsigned long now = micros();
  if (!s1_triggered && (now - last_trigger_time > DEBOUNCE_US)) {
    t1_micros = now;
    s1_triggered = true;
    last_trigger_time = now;
  }
}

void IRAM_ATTR isr_sensor_2() {
  unsigned long now = micros();
  if (s1_triggered && !s2_triggered && (now - t1_micros > DEBOUNCE_US)) {
    t2_micros = now;
    s2_triggered = true;
  }
}

void IRAM_ATTR isr_sensor_3() {
  unsigned long now = micros();
  if (s1_triggered && s2_triggered && !s3_triggered && (now - t2_micros > DEBOUNCE_US)) {
    t3_micros = now;
    s3_triggered = true;
    run_completed = true;
  }
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[WS] Cliente [%u] desconectado.\n", num);
      break;
    case WStype_CONNECTED: {
      IPAddress ip = webSocket.remoteIP(num);
      Serial.printf("[WS] Cliente [%u] conectado de %d.%d.%d.%d\n", num, ip[0], ip[1], ip[2], ip[3]);
      
      StaticJsonDocument<200> doc;
      doc["msg"] = "VeloTrilho ESP32 Pronto";
      doc["status"] = "ready";
      doc["run_id"] = run_counter;
      String output;
      serializeJson(doc, output);
      webSocket.sendTXT(num, output);
      break;
    }
    case WStype_TEXT: {
      Serial.printf("[WS] Comando recebido do Dashboard: %s\n", payload);
      StaticJsonDocument<256> inDoc;
      DeserializationError err = deserializeJson(inDoc, payload);
      if (!err) {
        const char* cmd = inDoc["command"] | "";
        if (strcmp(cmd, "reset") == 0) {
          resetSensors();
        } else if (strcmp(cmd, "set_servo") == 0) {
          int angle = inDoc["angle"] | 0;
          angle = constrain(angle, 0, 90);
          servoTrilho.write(angle);
          currentServoAngle = angle;
          Serial.printf("[SERVO] Inclinação ajustada para %d graus\n", angle);
        }
      } else if (strstr((char*)payload, "reset") != NULL) {
        resetSensors();
      }
      break;
    }
    default:
      break;
  }
}

void resetSensors() {
  noInterrupts();
  s1_triggered = false;
  s2_triggered = false;
  s3_triggered = false;
  run_completed = false;
  t1_micros = 0;
  t2_micros = 0;
  t3_micros = 0;
  interrupts();
  Serial.println("[SISTEMA] Sensores resetados. Aguardando novo disparo do carrinho...");
}

void transmitRunData() {
  double dt12 = (double)(t2_micros - t1_micros) / 1000000.0;
  double dt23 = (double)(t3_micros - t2_micros) / 1000000.0;
  double dt_total = (double)(t3_micros - t1_micros) / 1000000.0;

  double v12 = (D2 - D1) / dt12;
  double v23 = (D3 - D2) / dt23;
  double v_med = (D3 - D1) / dt_total;

  double dt_médio = (dt12 + dt23) / 2.0;
  double accel = (v23 - v12) / dt_médio;

  StaticJsonDocument<512> doc;
  doc["run_id"] = run_counter;
  doc["unit"] = "micros";
  
  doc["d1"] = D1;
  doc["d2"] = D2;
  doc["d3"] = D3;
  
  doc["t1"] = t1_micros;
  doc["t2"] = t2_micros;
  doc["t3"] = t3_micros;
  
  doc["dt12"] = dt12;
  doc["dt23"] = dt23;
  doc["dt_total"] = dt_total;
  doc["v12"] = v12;
  doc["v23"] = v23;
  doc["v_med"] = v_med;
  doc["acceleration"] = accel;

  String jsonString;
  serializeJson(doc, jsonString);

  Serial.println("\n-------------------------------------------");
  Serial.printf(">>> ENSAIO #%lu CONCLUÍDO <<<\n", run_counter);
  Serial.printf("Trecho 1 (0 -> 0.5m): Δt = %.4f s | v = %.3f m/s\n", dt12, v12);
  Serial.printf("Trecho 2 (0.5 -> 1.0m): Δt = %.4f s | v = %.3f m/s\n", dt23, v23);
  Serial.printf("Velocidade Total: %.3f m/s | Aceleração: %.3f m/s²\n", v_med, accel);
  Serial.println("Enviando via WebSocket para o Streamlit...");
  Serial.println(jsonString);
  Serial.println("-------------------------------------------\n");

  webSocket.broadcastTXT(jsonString);

  run_counter++;
  delay(1000);
  resetSensors();
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==========================================");
  Serial.println("     INICIALIZANDO SISTEMA VELOTRILHO     ");
  Serial.println("==========================================");

  pinMode(PIN_SENSOR_1, INPUT_PULLUP);
  pinMode(PIN_SENSOR_2, INPUT_PULLUP);
  pinMode(PIN_SENSOR_3, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(PIN_SENSOR_1), isr_sensor_1, FALLING);
  attachInterrupt(digitalPinToInterrupt(PIN_SENSOR_2), isr_sensor_2, FALLING);
  attachInterrupt(digitalPinToInterrupt(PIN_SENSOR_3), isr_sensor_3, FALLING);

  servoTrilho.attach(PIN_SERVO);
  servoTrilho.write(0);
  Serial.printf("[SERVO] SG90 inicializado no GPIO %d (angulo inicial: 0 deg)\n", PIN_SERVO);

  if (USE_ACCESS_POINT) {
    Serial.println("[WIFI] Criando Access Point VeloTrilho...");
    WiFi.softAP(AP_SSID, AP_PASS);
    IPAddress IP = WiFi.softAPIP();
    Serial.printf("[WIFI] Access Point Criado com Sucesso!\n");
    Serial.printf("[WIFI] SSID: %s | Senha: %s\n", AP_SSID, AP_PASS);
    Serial.print("[WIFI] IP do ESP32: ");
    Serial.println(IP);
    Serial.printf("[WS] Endereço WebSocket para colocar no Streamlit: ws://%s:%u\n", IP.toString().c_str(), WS_PORT);
  } else {
    Serial.printf("[WIFI] Conectando na rede: %s ...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }
    Serial.println("\n[WIFI] Conectado!");
    Serial.print("[WIFI] IP atribuído: ");
    Serial.println(WiFi.localIP());
    Serial.printf("[WS] Endereço WebSocket para colocar no Streamlit: ws://%s:%u\n", WiFi.localIP().toString().c_str(), WS_PORT);
  }

  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.printf("[WS] Servidor WebSocket rodando na porta %u\n", WS_PORT);
  Serial.println("[SISTEMA] Aguardando o carrinho passar pelos sensores...");
}

void loop() {
  webSocket.loop();

  if (run_completed) {
    transmitRunData();
  }
}

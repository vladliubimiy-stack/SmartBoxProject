#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"   // см. firmware/include/config.h (Wi-Fi SSID и PASS)

// ============== MQTT ==============
static const char* MQTT_HOST = "192.168.0.14";   // поправь если брокер другой
static const uint16_t MQTT_PORT = 1883;
static const char* MQTT_CLIENT_ID = "ESP32Client";

// ============== PIN MAP ==============
static const uint8_t RELAY_PIN         = 13;  // свет
static const uint8_t SHUTTER_OPEN_PIN  = 26;  // рольставни "Открыть"
static const uint8_t SHUTTER_CLOSE_PIN = 27;  // рольставни "Закрыть"
static const uint8_t LIGHT_PIN         = 34;  // фоторезистор (ADC)

// ============== TOPICS ==============
static const char* T_RELAY_CMD     = "home/relay1";
static const char* T_SHUTTER_CMD   = "home/shutter";
static const char* T_LIGHT_SENSOR  = "home/lightsensor";

WiFiClient espClient;
PubSubClient client(espClient);

// ================= Wi-Fi =================
static void connectWiFi() {
  Serial.print("WiFi: connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(300);
    Serial.print('.');
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("\nWiFi connected, IP=");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi: FAILED, will retry in loop");
  }
}

// ================= SHUTTER =================
static void pulsePin(uint8_t pin, uint32_t ms = 1000) {
  if (pin == SHUTTER_OPEN_PIN)  digitalWrite(SHUTTER_CLOSE_PIN, LOW);
  if (pin == SHUTTER_CLOSE_PIN) digitalWrite(SHUTTER_OPEN_PIN, LOW);

  digitalWrite(pin, HIGH);
  delay(ms);
  digitalWrite(pin, LOW);
}

static void shutterOpen()  { Serial.println("SHUTTER: OPEN");  pulsePin(SHUTTER_OPEN_PIN); }
static void shutterClose() { Serial.println("SHUTTER: CLOSE"); pulsePin(SHUTTER_CLOSE_PIN); }
static void shutterStop()  {
  Serial.println("SHUTTER: STOP");
  digitalWrite(SHUTTER_OPEN_PIN, LOW);
  digitalWrite(SHUTTER_CLOSE_PIN, LOW);
}

// ================= MQTT CALLBACK =================
static void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  static char buf[64];
  unsigned int n = min((unsigned int)(sizeof(buf) - 1), length);
  memcpy(buf, payload, n);
  buf[n] = '\0';
  String message = String(buf);

  Serial.print("MQTT IN [");
  Serial.print(topic);
  Serial.print("] '");
  Serial.print(message);
  Serial.println("'");

  if (String(topic) == T_RELAY_CMD) {
    if (message == "ON")  { digitalWrite(RELAY_PIN, HIGH); Serial.println("RELAY: ON"); }
    if (message == "OFF") { digitalWrite(RELAY_PIN, LOW);  Serial.println("RELAY: OFF"); }
  }

  if (String(topic) == T_SHUTTER_CMD) {
    if (message == "OPEN")  shutterOpen();
    if (message == "CLOSE") shutterClose();
    if (message == "STOP")  shutterStop();
  }
}

// ================= MQTT RECONNECT =================
static void ensureMqtt() {
  if (client.connected()) return;

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    if (WiFi.status() != WL_CONNECTED) {
      delay(1000);
      return;
    }
  }

  Serial.print("MQTT: connecting to ");
  Serial.print(MQTT_HOST);
  Serial.print(':');
  Serial.println(MQTT_PORT);
  if (client.connect(MQTT_CLIENT_ID)) {
    Serial.println("MQTT: connected");
    client.subscribe(T_RELAY_CMD);
    client.subscribe(T_SHUTTER_CMD);
    Serial.println("MQTT: subscribed");
  } else {
    Serial.print("MQTT: failed, rc=");
    Serial.println(client.state());
    delay(1500);
  }
}

// ================= Arduino =================
void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  pinMode(SHUTTER_OPEN_PIN, OUTPUT);
  pinMode(SHUTTER_CLOSE_PIN, OUTPUT);
  digitalWrite(SHUTTER_OPEN_PIN, LOW);
  digitalWrite(SHUTTER_CLOSE_PIN, LOW);

  // LIGHT_PIN — ADC, pinMode не обязателен, но можно явно
  pinMode(LIGHT_PIN, INPUT);

  connectWiFi();

  client.setServer(MQTT_HOST, MQTT_PORT);
  client.setCallback(onMqttMessage);
}

void loop() {
  ensureMqtt();
  client.loop();

  // --- публикация света ---
  static uint32_t lastPub = 0;
  if (millis() - lastPub > 2000) {  // каждые 2 секунды
    int val = analogRead(LIGHT_PIN);
    char buf[16];
    itoa(val, buf, 10);
    client.publish(T_LIGHT_SENSOR, buf);
    lastPub = millis();
    Serial.print("LIGHT: ");
    Serial.println(val);
  }
}

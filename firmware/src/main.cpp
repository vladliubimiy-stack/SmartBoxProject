#include <WiFi.h>
#include <PubSubClient.h>
#include "LightRelay.h"
#include "ShutterControl.h"
#include "LightSensor.h"   // добавляем датчик света

const char* ssid = "SHINKA";
const char* password = "zaminetskazhu";
const char* mqtt_server = "192.168.0.14";
const uint16_t mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

// Реле на пине 13
LightRelay light(13, &client, "home/relay1");

// Сенсор света (A0 на ESP32 это pin 36 или 34 чаще всего)
LightSensor lightSensor(34);

unsigned long lastSensorSend = 0;

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected. IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi");
  }
}

void maintainWiFi() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
}

void mqttReconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT broker... ");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
      client.subscribe("home/relay1");
      subscribeShutter(client);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String topicStr = String(topic);
  String message;
  for (int i = 0; i < length; i++) message += (char)payload[i];

  if (topicStr == "home/relay1") light.handleMessage(message);
  routeShutterCallback(topic, payload, length);
}

void setup() {
  Serial.begin(115200);
  light.begin();
  lightSensor.begin();       // инициализация датчика
  initShutterPins();
  connectWiFi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  maintainWiFi();
  if (!client.connected()) mqttReconnect();
  client.loop();

  // Отправляем данные с датчика каждые 5 сек
  if (millis() - lastSensorSend > 5000) {
    int value = lightSensor.read();
    char msg[16];
    sprintf(msg, "%d", value);
    client.publish("home/lightsensor", msg);
    Serial.print("LightSensor -> ");
    Serial.println(msg);
    lastSensorSend = millis();
  }
}

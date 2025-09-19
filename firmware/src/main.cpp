#include <WiFi.h>
#include <PubSubClient.h>
#include "LightRelay.h"
#include "ShutterControl.h"
#include "config.h"   

const char* mqtt_server = "192.168.0.14"; // Ваш ip
const uint16_t mqtt_port = 1883;          // Ваш порт

WiFiClient espClient;
PubSubClient client(espClient);

// пример твоего реле
LightRelay light(13, &client, "home/relay1");

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

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
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    connectWiFi();
  }
}

void setup() {
  Serial.begin(115200);
  connectWiFi();
  client.setServer(mqtt_server, mqtt_port);
  // тут можешь добавить client.setCallback(...)
}

void loop() {
  maintainWiFi();
  if (!client.connected()) {
    // подключение к MQTT
    while (!client.connected()) {
      Serial.print("Connecting to MQTT...");
      if (client.connect("ESP32Client")) {
        Serial.println("connected");
        client.subscribe("home/#");
      } else {
        Serial.print("failed, rc=");
        Serial.print(client.state());
        delay(2000);
      }
    }
  }
  client.loop();
}

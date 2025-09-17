#include "LightRelay.h"


LightRelay::LightRelay(int relayPin, PubSubClient* mqttClient, const char* topic) {
pin = relayPin;
client = mqttClient;
statusTopic = topic;
relayState = false; // по умолчанию выключено
}


void LightRelay::begin() {
pinMode(pin, OUTPUT);
digitalWrite(pin, LOW);
}


void LightRelay::handleMessage(const String& message) {
// Включаем только если реально нужно
if(message == "ON" && !relayState) {
digitalWrite(pin, HIGH);
relayState = true;
publishStatus("ON");
} else if(message == "OFF" && relayState) {
digitalWrite(pin, LOW);
relayState = false;
publishStatus("OFF");
}
}


void LightRelay::publishStatus(const char* status) {
if(client->connected()) {
client->publish(statusTopic, status);
}
}
#ifndef LIGHT_RELAY_H
#define LIGHT_RELAY_H


#include <PubSubClient.h>
#include <Arduino.h>


class LightRelay {
private:
int pin;
PubSubClient* client;
const char* statusTopic;
bool relayState; // текущее состояние реле


public:
LightRelay(int relayPin, PubSubClient* mqttClient, const char* topic);
void begin();
void handleMessage(const String& message);
void publishStatus(const char* status);
};


#endif
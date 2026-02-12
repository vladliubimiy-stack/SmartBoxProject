#ifndef SHUTTER_CONTROL_H
#define SHUTTER_CONTROL_H


#include <Arduino.h>
#include <PubSubClient.h>


const int shutterOpenPin = 26;
const int shutterClosePin = 27;


void initShutterPins();
void triggerShutter(int pin);
void handleShutterMessage(const String& topic, const String& message);
void subscribeShutter(PubSubClient& client);
void routeShutterCallback(char* topic, byte* payload, unsigned int length);


#endif
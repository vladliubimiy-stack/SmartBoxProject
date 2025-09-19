#include "ShutterControl.h"


void initShutterPins() {
pinMode(shutterOpenPin, OUTPUT);
pinMode(shutterClosePin, OUTPUT);
digitalWrite(shutterOpenPin, LOW);
digitalWrite(shutterClosePin, LOW);
}


void triggerShutter(int pin) {
digitalWrite(pin, HIGH);
delay(1000);
digitalWrite(pin, LOW);
}


void handleShutterMessage(const String& topic, const String& message) {
if (message == "OPEN" || message == "STOP_OPEN") {
triggerShutter(shutterOpenPin);
} else if (message == "CLOSE" || message == "STOP_CLOSE") {
triggerShutter(shutterClosePin);
}
}


void subscribeShutter(PubSubClient& client) {
client.subscribe("home/shutter");
}


void routeShutterCallback(char* topic, byte* payload, unsigned int length) {
String topicStr = String(topic);
String message;
for (unsigned int i = 0; i < length; i++) message += (char)payload[i];


if (topicStr == "home/shutter") handleShutterMessage(topicStr, message);
}
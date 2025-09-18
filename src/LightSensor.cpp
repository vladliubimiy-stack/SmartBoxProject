#include "lightsensor.h"

LightSensor::LightSensor(uint8_t pin) {
    _pin = pin;
}

void LightSensor::begin() {
    pinMode(_pin, INPUT);
}

int LightSensor::read() {
    return analogRead(_pin);
}

bool LightSensor::isDark(int threshold) {
    return analogRead(_pin) < threshold;
}

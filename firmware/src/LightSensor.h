#ifndef LIGHTSENSOR_H
#define LIGHTSENSOR_H

#include <Arduino.h>

class LightSensor {
public:
    LightSensor(uint8_t pin);
    void begin();
    int read();
    bool isDark(int threshold = 500);

private:
    uint8_t _pin;
};

#endif

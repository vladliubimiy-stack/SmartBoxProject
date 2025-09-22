#pragma once
#include <Arduino.h>
#include <Adafruit_HTU21DF.h>

class Climat {
public:
    Climat();
    bool begin();                   // инициализация датчика
    float getTemperature();         // вернуть температуру
    float getHumidity();            // вернуть влажность
    String getReport();             // строка для телеги
private:
    Adafruit_HTU21DF sht;
};

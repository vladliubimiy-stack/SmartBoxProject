#include "climat.h"

Climat::Climat() : sht() {}

bool Climat::begin() {
    return sht.begin();  // внутри сама дернет Wire.begin() на дефолтных SDA=21, SCL=22
}

float Climat::getTemperature() {
    return sht.readTemperature();
}

float Climat::getHumidity() {
    return sht.readHumidity();
}

String Climat::getReport() {
    float t = getTemperature();
    float h = getHumidity();

    String msg = "🌡 Температура: ";
    msg += String(t, 1);
    msg += " °C\n💧 Влажность: ";
    msg += String(h, 1);
    msg += " %";
    return msg;
}

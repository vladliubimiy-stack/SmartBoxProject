# SmartBoxProject

SmartBox is an ESP32-based smart workshop box. The firmware controls a relay and shutter/roller door over MQTT and publishes light and climate readings. The supported Telegram bot is firmware/tgbot/telebot_mqtt.py. The root-level tgbot/telebot_mqtt.py is a compatibility launcher for that same implementation.

## Security notice

Credentials were committed in tracked example files. Treat the previously exposed Wi-Fi password and Telegram bot token as compromised: change the Wi-Fi password and revoke the old bot token in BotFather. Replacing the current example files does not erase credentials from Git history.

The MQTT broker now rejects anonymous connections. Create unique credentials for smartbox, telegram, and jarvis; keep password files and local config files out of Git. The Telegram bot refuses to start without an explicit user-ID allowlist and MQTT credentials.

## MQTT broker setup

Run these commands from the repository root on the computer that hosts Mosquitto. The password commands prompt for each secret; do not put secrets into shell history.

~~~text
mosquitto_passwd -c mosquitto/passwd smartbox
mosquitto_passwd mosquitto/passwd telegram
mosquitto_passwd mosquitto/passwd jarvis
mosquitto -c mosquitto/mosquitto.conf -v
~~~

The committed mosquitto/acl file grants the ESP32 access to command topics and sensor publishing, the Telegram bridge access to commands and readings, and Jarvis access to the two actuator command topics. If Mosquitto runs as a Windows service, update password_file and acl_file in mosquitto/mosquitto.conf to absolute paths readable by that service.

## ESP32 firmware setup

1. Copy firmware/include/config_example.h to firmware/include/config.h.
2. Set your Wi-Fi name and password, the broker's LAN IP or host name, and the smartbox MQTT username/password in config.h.
3. Build and upload the firmware from firmware with PlatformIO.

config.h is ignored by Git. Do not add it to a commit.

## Telegram bot setup

1. Create firmware/tgbot/.env from firmware/tgbot/.env.example.
2. Add a newly issued BotFather token and your numeric Telegram user ID to ALLOWED_TELEGRAM_USER_IDS. Multiple allowed IDs may be comma-separated.
3. Set MQTT_USER=telegram and the matching password. Set MQTT_BIND_IFACE to the broker computer's network adapter name, for example Ethernet 2 on Windows. The startup script writes the current broker-host IPv4 address to the ignored .env.runtime file.
4. Install the bot requirements and start the canonical entry point:

~~~powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r firmware/tgbot/requirements.txt
python firmware/tgbot/telebot_mqtt.py
~~~

The root-level tgbot/telebot_mqtt.py forwards to the same entry point. Its configuration still lives in firmware/tgbot/.env.

## Jarvis integration

Set Jarvis's local .env MQTT_HOST to the same broker address and use the jarvis MQTT account. The broker must be reachable from both the Windows computer and ESP32. MQTT_HOST=127.0.0.1 works only for a client running on the broker computer.

## Automated checks

The dependency-free access-control checks run locally and in GitHub Actions:

~~~powershell
python -m unittest discover -s tests
~~~

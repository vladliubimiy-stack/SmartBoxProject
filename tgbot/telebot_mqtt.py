# bot/bot.py
import os
import time
from dotenv import load_dotenv
import telebot
import paho.mqtt.client as mqtt

# грузим переменные окружения из bot/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

BOT_TOKEN   = os.getenv("BOT_TOKEN")
MQTT_BROKER = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER   = os.getenv("MQTT_USER")
MQTT_PASS   = os.getenv("MQTT_PASSWORD")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Заполни bot/.env или переменные окружения.")

bot = telebot.TeleBot(BOT_TOKEN)

# глобально храним последнее значение датчика
last_light_value = None

# один постоянный MQTT-клиент: подписки + публикации
mqtt_client = mqtt.Client(client_id="tg-bridge")
if MQTT_USER:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

def on_connect(client, userdata, flags, rc):
    print("MQTT connected with code", rc)
    client.subscribe("home/lightsensor")

def on_message(client, userdata, msg):
    global last_light_value
    if msg.topic == "home/lightsensor":
        try:
            last_light_value = int(msg.payload.decode())
        except Exception:
            last_light_value = None

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ====== функции проверки света ======
def try_switch_light(command, target_state, chat_id):
    """
    command: "ON" или "OFF"
    target_state: "on" или "off"
    """
    global last_light_value

    for _ in range(5):
        # публикуем команду без нового подключения
        mqtt_client.publish("home/relay1", command, qos=0, retain=False)

        time.sleep(2)
        val = last_light_value
        print("LightSensor:", val)

        if val is None:
            continue

        if target_state == "on" and val < 1300:
            bot.send_message(chat_id, "✅ Свет включен")
            return
        if target_state == "off" and val > 2200:
            bot.send_message(chat_id, "✅ Свет выключен")
            return

    bot.send_message(chat_id, "❌ Что-то пошло по пизде, иди чини")

# ====== Telegram-обработчики ======
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💡 Включить свет", "🔌 Выключить свет")
    markup.add("⬆️ Открыть ворота", "⬇️ Закрыть ворота")
    bot.send_message(message.chat.id, "Йо брат, управляй умным домом:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    text = message.text

    if text == "💡 Включить свет":
        try_switch_light("ON", "on", message.chat.id)

    elif text == "🔌 Выключить свет":
        try_switch_light("OFF", "off", message.chat.id)

    elif text == "⬆️ Открыть ворота":
        mqtt_client.publish("home/shutter", "OPEN")
        bot.send_message(message.chat.id, "⬆️ Открываю ворота")

    elif text == "⬇️ Закрыть ворота":
        mqtt_client.publish("home/shutter", "CLOSE")
        bot.send_message(message.chat.id, "⬇️ Закрываю ворота")

    else:
        bot.send_message(message.chat.id, "Не понял команду, братишка.")

print("Бот запущен...")
bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)

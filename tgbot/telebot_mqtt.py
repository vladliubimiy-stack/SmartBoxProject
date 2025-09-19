import telebot
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import time

BOT_TOKEN = '8485869663:AAG2TBAIFJ9oZaNR60TKwHTYf4Ji8l-Z9h0'
MQTT_BROKER = '192.168.0.14'
MQTT_PORT = 1883

bot = telebot.TeleBot(BOT_TOKEN)

# глобально храним последнее значение датчика
last_light_value = None

# создаём MQTT клиент для подписки
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("MQTT connected with code", rc)
    client.subscribe("home/lightsensor")

def on_message(client, userdata, msg):
    global last_light_value
    if msg.topic == "home/lightsensor":
        try:
            last_light_value = int(msg.payload.decode())
        except:
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

    for attempt in range(5):
        # шлём команду на ESP
        publish.single("home/relay1", command, hostname=MQTT_BROKER, port=MQTT_PORT)

        # ждём обновления датчика
        time.sleep(2)
        val = last_light_value
        print("LightSensor:", val)

        if val is None:
            continue

        # проверка включения
        if target_state == "on" and val < 1300:
            bot.send_message(chat_id, "✅ Свет включен")
            return
        # проверка выключения
        if target_state == "off" and val > 2200:
            bot.send_message(chat_id, "✅ Свет выключен")
            return

    # если 5 раз не получилось
    bot.send_message(chat_id, "❌ Что-то пошло по пизде, иди чини")


# ====== бота запускаем ======
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
        publish.single("home/shutter", "OPEN", hostname=MQTT_BROKER, port=MQTT_PORT)
        bot.send_message(message.chat.id, "⬆️ Открываю ворота")

    elif text == "⬇️ Закрыть ворота":
        publish.single("home/shutter", "CLOSE", hostname=MQTT_BROKER, port=MQTT_PORT)
        bot.send_message(message.chat.id, "⬇️ Закрываю ворота")

    else:
        bot.send_message(message.chat.id, "Не понял команду, братишка.")


print("Бот запущен...")
bot.infinity_polling()

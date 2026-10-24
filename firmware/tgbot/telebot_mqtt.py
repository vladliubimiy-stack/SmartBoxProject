import logging
import os
import subprocess
import sys
import time
from dotenv import load_dotenv
import telebot
import paho.mqtt.client as mqtt
from access_control import is_allowed_user, parse_allowed_user_ids

BASE_DIR = os.path.dirname(__file__)
DEFAULT_ENV_PATH = os.path.join(BASE_DIR, ".env")
RUNTIME_ENV_PATH = os.path.join(BASE_DIR, ".env.runtime")
RENDER_SCRIPT_PATH = os.path.join(BASE_DIR, "scripts", "render_mqtt_env.py")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("telebot_mqtt")

# грузим статические переменные из tgbot/.env (например BOT_TOKEN)
load_dotenv(dotenv_path=DEFAULT_ENV_PATH)


def refresh_runtime_env() -> None:
    """Перегенерирует runtime env c актуальным MQTT_HOST и MQTT_PORT."""
    try:
        result = subprocess.run(
            [sys.executable, RENDER_SCRIPT_PATH, "--output", RUNTIME_ENV_PATH],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            logger.info(result.stdout.strip())
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        logger.error("Не удалось обновить runtime env: %s", details)
        raise RuntimeError(
            "MQTT_HOST не определен: скрипт render_mqtt_env.py не смог определить IPv4 адрес. "
            "Проверьте MQTT_BIND_IFACE и сетевые интерфейсы."
        ) from exc


refresh_runtime_env()
# явно грузим runtime env, который перегенерируется при старте
load_dotenv(dotenv_path=RUNTIME_ENV_PATH, override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MQTT_BROKER = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASSWORD")
ALLOWED_TELEGRAM_USER_IDS = parse_allowed_user_ids(os.getenv("ALLOWED_TELEGRAM_USER_IDS"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Заполни tgbot/.env или переменные окружения.")

if not MQTT_BROKER:
    logger.error(
        "MQTT_HOST пустой. Укажите MQTT_BIND_IFACE (например wlan0/eth0) "
        "или настройте MQTT_HOST вручную в tgbot/.env."
    )
    raise RuntimeError("MQTT_HOST не задан, запуск бота остановлен.")

if not MQTT_USER or not MQTT_PASS:
    raise RuntimeError("MQTT_USER и MQTT_PASSWORD обязательны. Заполните локальный .env.")

bot = telebot.TeleBot(BOT_TOKEN)

# глобально храним последние значения датчиков
last_light_value = None
last_climat_report = None

# один постоянный MQTT-клиент: подписки + публикации
mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="tg-bridge")
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)


def on_connect(client, userdata, flags, reason_code, properties):
    logger.info("MQTT connected with code %s", reason_code)
    client.subscribe("home/lightsensor")
    client.subscribe("home/climat/report")  # подписка на климат


def on_message(client, userdata, msg):
    global last_light_value, last_climat_report
    if msg.topic == "home/lightsensor":
        try:
            last_light_value = int(msg.payload.decode())
        except Exception:
            last_light_value = None
    elif msg.topic == "home/climat/report":
        last_climat_report = msg.payload.decode()


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

    # Команду отправляем сразу
    mqtt_client.publish("home/relay1", command, qos=0, retain=False)

    # Если датчик еще ничего не прислал — не блокируем бота длинным ожиданием
    if last_light_value is None:
        logger.warning("LightSensor: нет данных от MQTT topic home/lightsensor")
        bot.send_message(chat_id, "⚠️ Команда отправлена, но датчик света пока не прислал данные. Проверь MQTT topic home/lightsensor.")
        return

    for _ in range(5):
        time.sleep(1)
        val = last_light_value
        logger.info("LightSensor: %s", val)

        if target_state == "on" and val is not None and val < 1300:
            bot.send_message(chat_id, "✅ Свет включен")
            return
        if target_state == "off" and val is not None and val > 2200:
            bot.send_message(chat_id, "✅ Свет выключен")
            return

    bot.send_message(chat_id, "⚠️ Команда отправлена, но подтверждение от датчика не получено")


# ====== Telegram-обработчики ======
def is_authorized(message):
    user = getattr(message, "from_user", None)
    user_id = getattr(user, "id", None)
    if is_allowed_user(user_id, ALLOWED_TELEGRAM_USER_IDS):
        return True
    logger.warning("Rejected Telegram user %s", user_id)
    bot.send_message(message.chat.id, "Доступ запрещён.")
    return False


@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_authorized(message):
        return
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💡 Включить свет", "🔌 Выключить свет")
    markup.add("⬆️ Открыть ворота", "⬇️ Закрыть ворота")
    markup.add("🌡 Температура в боксе")  # новая кнопка
    bot.send_message(message.chat.id, "Йо брат, управляй умным домом:", reply_markup=markup)


@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    if not is_authorized(message):
        return
    text = (message.text or "").strip()

    try:
        if "Включить свет" in text:
            try_switch_light("ON", "on", message.chat.id)

        elif "Выключить свет" in text:
            try_switch_light("OFF", "off", message.chat.id)

        elif "Открыть ворота" in text:
            mqtt_client.publish("home/shutter", "OPEN")
            bot.send_message(message.chat.id, "⬆️ Открываю ворота")

        elif "Закрыть ворота" in text:
            mqtt_client.publish("home/shutter", "CLOSE")
            bot.send_message(message.chat.id, "⬇️ Закрываю ворота")

        elif "Температура в боксе" in text:
            if last_climat_report:
                bot.send_message(message.chat.id, last_climat_report)
            else:
                bot.send_message(message.chat.id, "❌ Климат ещё не прислал данные")

        else:
            bot.send_message(message.chat.id, "Не понял команду, братишка.")
    except Exception as exc:
        logger.exception("Ошибка в обработчике сообщения: %s", exc)
        bot.send_message(message.chat.id, "❌ Внутренняя ошибка обработки команды")


print("Бот запущен...")
bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)

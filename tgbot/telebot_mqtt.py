"""Compatibility launcher for the supported Telegram bot."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    entrypoint = Path(__file__).resolve().parents[1] / "firmware" / "tgbot" / "telebot_mqtt.py"
    runpy.run_path(str(entrypoint), run_name="__main__")

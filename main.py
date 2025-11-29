import os
import requests
from bs4 import BeautifulSoup
import telebot

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)

MANU_NAMES = ["Манчестер Юнайтед", "Manchester United"]
CSKA_NAMES = ["ЦСКА", "CSKA"]

URL = "https://www.championat.com/stat/"

def find_matches():
    resp = requests.get(URL, timeout=20)
    resp.raise_for_status()
    html = resp.text
    manu_found = any(name in html for name in MANU_NAMES)
    cska_found = any(name in html for name in CSKA_NAMES)
    results = []
    if manu_found:
        results.append("Есть матч с участием Манчестер Юнайтед на championat.com")
    if cska_found:
        results.append("Есть матч с участием ЦСКА Москва на championat.com")
    return results

def send_notifications():
    matches = find_matches()
    if not matches:
        return
    text = "Напоминание о матчах:\n\n" + "\n".join(f"- {m}" for m in matches)
    bot.send_message(CHAT_ID, text)

if __name__ == "__main__":
    send_notifications()

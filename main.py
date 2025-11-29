import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)

MANU_URL = "https://www.sports.ru/football/club/mu/calendar/"
CSKA_URL = "https://www.sports.ru/football/club/cska/calendar/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9"
}

def get_upcoming_matches(url, team_name):
    print(f"Загрузка {team_name}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        matches = []
        today = datetime.now()
        week_later = today + timedelta(days=7)
        
        # Ищем все ссылки с текстом "превью" - это будущие матчи
        preview_links = soup.find_all('a', string='превью')
        print(f"Найдено 'превью' ссылок: {len(preview_links)}")
        
        for link in preview_links:
            href = link.get('href', '')
            print(f"\nОбработка: {href}")
            
            # Поднимаемся по DOM чтобы найти дату и название матча
            parent = link.parent
            row_text = ""
            
            # Пробуем найти строку таблицы
            for _ in range(5):
                if parent is None:
                    break
                row_text = parent.get_text(separator=' ', strip=True)
                if re.search(r'\d{2}\.\d{2}\.\d{4}', row_text):
                    break
                parent = parent.parent
            
            print(f"  Row text: {row_text[:100]}...")
            
            # Ищем дату и время
            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4}).*?(\d{2}:\d{2})', row_text)
            if not date_match:
                print("  Дата не найдена")
                continue
            
            day, month, year, time = date_match.groups()
            dt_msk = datetime.strptime(f"{day}.{month}.{year} {time}", "%d.%m.%Y %H:%M")
            print(f"  Дата МСК: {dt_msk}")
            
            # Проверяем диапазон 7 дней
            if not (today <= dt_msk <= week_later):
                print(f"  Не в диапазоне")
                continue
            
            # Конвертация MSK->IL (-1 час)
            dt_il = dt_msk - timedelta(hours=1)
            
            # Ищем название матча
            # Формат: "Команда А - Команда Б" или с разными тире
            match_pattern = re.search(r'([\w\s]+?)\s*[\-\u2013\u2014]\s*([\w\s]+?)\s*(?:-\s*:\s*-|\d+\s*:\s*\d+|\u043f\u0440\u0435\u0432\u044c\u044e)', row_text)
            if match_pattern:
                team1, team2 = match_pattern.groups()
                match_title = f"{team1.strip()} - {team2.strip()}"
            else:
                # Альтернативный поиск соперника
                match_title = "vs ?"
                # Ищем ссылку с полным названием матча
                parent = link.parent
                for _ in range(5):
                    if parent is None:
                        break
                    for a in parent.find_all('a'):
                        a_text = a.get_text(strip=True)
                        if ' - ' in a_text or ' \u2013 ' in a_text:
                            match_title = a_text.replace('- : -', '').replace('\u043f\u0440\u0435\u0432\u044c\u044e', '').strip()
                            break
                    if match_title != "vs ?":
                        break
                    parent = parent.parent
            
            print(f"  Матч: {match_title}")
            
            # Форматируем
            months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            
            entry = (
                f"📅 {dt_il.day} {months_ru[dt_il.month - 1]}\n"
                f"🕐 {dt_il.strftime('%H:%M')} (Иерусалим)\n"
                f"⚽ {match_title}"
            )
            matches.append(entry)
            print(f"  ✓ Добавлен")
        
        print(f"\nВсего матчей {team_name}: {len(matches)}")
        return matches
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def send_notifications():
    manu = get_upcoming_matches(MANU_URL, "Manchester United")
    cska = get_upcoming_matches(CSKA_URL, "CSKA Moscow")
    
    if not manu and not cska:
        print("Матчей нет")
        return
    
    text = "🏆 <b>Матчи на 7 дней:</b>\n\n"
    if manu:
        text += "🔴 <b>ManU:</b>\n" + "\n\n".join(manu) + "\n\n"
    if cska:
        text += "🔵 <b>ЦСКА:</b>\n" + "\n\n".join(cska)
    
    print(f"\n=== Сообщение ===\n{text}")
    
    try:
        bot.send_message(CHAT_ID, text, parse_mode='HTML', disable_web_page_preview=True)
        print("Отправлено!")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    send_notifications()

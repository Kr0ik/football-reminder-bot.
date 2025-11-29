import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# URLs
MANU_URL = "https://www.sports.ru/football/club/mu/calendar/"
CSKA_URL = "https://www.sports.ru/football/club/cska/calendar/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
        
        # Новый подход: ищем ссылки с будущими матчами
        # Будущие матчи имеют формат "Команда А – Команда Б - : -"
        all_links = soup.find_all('a')
        print(f"Найдено ссылок: {len(all_links)}")
        
        # Словарь для хранения дат по href
        date_map = {}
        match_map = {}
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Ищем ссылки с датами (формат DD.MM.YYYY|HH:MM)
            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})\|(\d{2}:\d{2})', text)
            if date_match:
                day, month, year, time = date_match.groups()
                date_map[href] = f"{day}.{month}.{year} {time}"
            
            # Ищем ссылки с будущими матчами (содержат " – " и "- : -")
            if ' – ' in text and '- : -' in text:
                # Убираем счет из названия
                match_title = text.replace(' - : -', '').strip()
                match_map[href] = match_title
                print(f"Найден будущий матч: {match_title} (href: {href})")
        
        # Теперь сопоставляем матчи с датами
        for href, match_title in match_map.items():
            # Ищем дату для этого матча
            date_str = None
            
            # Пробуем найти по части href
            for date_href, date_val in date_map.items():
                # Проверяем совпадение по дате в href
                if '/football/match/' in href:
                    match_date_part = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    if match_date_part in date_href or date_href in href:
                        date_str = date_val
                        break
            
            # Если не нашли по href, ищем дату из текста страницы
            if not date_str:
                # Ищем в HTML рядом с матчем
                match_link = soup.find('a', href=href)
                if match_link:
                    parent = match_link.parent
                    if parent:
                        parent_text = parent.get_text()
                        date_search = re.search(r'(\d{2})\.(\d{2})\.(\d{4}).*?(\d{2}:\d{2})', parent_text)
                        if date_search:
                            day, month, year, time = date_search.groups()
                            date_str = f"{day}.{month}.{year} {time}"
            
            if not date_str:
                print(f"  Не найдена дата для матча: {match_title}")
                continue
            
            print(f"  Дата: {date_str}")
            
            # Парсим дату
            try:
                dt_msk = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
            except:
                print(f"  Ошибка парсинга даты: {date_str}")
                continue
            
            # Проверяем диапазон
            if not (today <= dt_msk <= week_later):
                print(f"  Матч не в диапазоне 7 дней")
                continue
            
            # Конвертация времени (Москва UTC+3 -> Израиль UTC+2)
            dt_il = dt_msk - timedelta(hours=1)
            
            # Форматирование
            months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            
            day_str = dt_il.strftime("%d")
            month_str = months_ru[dt_il.month - 1]
            time_str = dt_il.strftime("%H:%M")
            
            entry = (
                f"📅 {day_str} {month_str}\n"
                f"🕐 {time_str} (Иерусалим)\n"
                f"⚽ {match_title}"
            )
            matches.append(entry)
            print(f"  ✓ Добавлен матч")
        
        print(f"Всего матчей для {team_name}: {len(matches)}")
        return matches
    except Exception as e:
        print(f"Error fetching {team_name}: {e}")
        import traceback
        traceback.print_exc()
        return []

def send_notifications():
    manu_matches = get_upcoming_matches(MANU_URL, "Manchester United")
    cska_matches = get_upcoming_matches(CSKA_URL, "CSKA Moscow")
    
    if not manu_matches and not cska_matches:
        print("Матчей на неделю нет, сообщение не отправляем.")
        return
    
    text_parts = ["🏆 <b>Матчи на ближайшие 7 дней:</b>\n\n"]
    
    if manu_matches:
        text_parts.append("🔴 <b>Манчестер Юнайтед:</b>\n")
        text_parts.append("\n\n".join(manu_matches))
        text_parts.append("\n\n")
    
    if cska_matches:
        text_parts.append("🔵 <b>ЦСКА Москва:</b>\n")
        text_parts.append("\n\n".join(cska_matches))
    
    text = ''.join(text_parts)
    
    print(f"\n=== СООБЩЕНИЕ ===")
    print(text)
    print("================\n")
    
    try:
        bot.send_message(CHAT_ID, text, parse_mode='HTML', disable_web_page_preview=True)
        print("Сообщение отправлено!")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

if __name__ == "__main__":
    send_notifications()

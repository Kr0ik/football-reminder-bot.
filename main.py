import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
from datetime import datetime, timedelta
import locale

# Попытка установить русскую локаль для дат (если система поддерживает)
try:
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
except:
    pass

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
        
        # Ищем таблицу с календарем
        table = soup.find('table')
        if not table:
            print(f"Таблица не найдена для {team_name}")
            return []
        
        rows = table.find_all('tr')
        print(f"Найдено строк: {len(rows)}")
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue  # Пропускаем заголовки
            
            # Проверяем, есть ли признак будущего матча
            row_text = row.get_text().lower()
            is_upcoming = ('превью' in row_text) or ('- : -' in row_text)
            
            if not is_upcoming:
                continue
            
            # DEBUG: выводим содержимое ячеек
            print(f"\n--- Найден будущий матч ---")
            for i, cell in enumerate(cells):
                print(f"  Cell[{i}]: {cell.get_text(strip=True)[:50]}")
            
            # Ячейка 0: Дата и время (формат "DD.MM.YYYY|HH:MM")
            date_cell = cells[0].get_text(strip=True)
            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4}).*?(\d{2}:\d{2})', date_cell)
            
            if not date_match:
                print(f"  Дата не распознана: {date_cell}")
                continue
            
            day, month, year, time = date_match.groups()
            dt_msk = datetime.strptime(f"{day}.{month}.{year} {time}", "%d.%m.%Y %H:%M")
            
            # Проверяем, попадает ли матч в ближайшие 7 дней
            if not (today <= dt_msk <= week_later):
                print(f"  Матч {dt_msk} не в диапазоне {today} - {week_later}")
                continue
            
            # КОНВЕРТАЦИЯ ВРЕМЕНИ (Москва UTC+3 -> Израиль UTC+2 зимой)
            dt_il = dt_msk - timedelta(hours=1)
            
            # Ячейка 2: Соперник (название команды)
            opponent = cells[2].get_text(strip=True) if len(cells) > 2 else "?"
            
            # Ищем полное название матча в последних ячейках
            # Обычно это ячейка с текстом типа "Команда А – Команда Б - : -"
            match_title = ""
            for cell in reversed(cells):
                cell_text = cell.get_text(strip=True)
                if ' – ' in cell_text and len(cell_text) > 10:
                    # Убираем счет из названия
                    match_title = re.sub(r'\s*-\s*:\s*-\s*$', '', cell_text).strip()
                    match_title = re.sub(r'\s*\d+\s*:\s*\d+\s*$', '', match_title).strip()
                    break
            
            # Если не нашли полное название, формируем из соперника
            if not match_title:
                match_title = f"vs {opponent}"
            
            print(f"  Match title: {match_title}")
            print(f"  Date (MSK): {dt_msk}, Date (IL): {dt_il}")
            
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
        
        print(f"\nВсего найдено матчей для {team_name}: {len(matches)}")
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
    
    print(f"\n=== ИТОГОВОЕ СООБЩЕНИЕ ===")
    print(text)
    print("=========================\n")
    
    # Отправка с parse_mode='HTML' для жирного текста
    try:
        bot.send_message(CHAT_ID, text, parse_mode='HTML', disable_web_page_preview=True)
        print("Сообщение отправлено!")
    except Exception as e:
        print(f"Ошибка отправки Telegram: {e}")

if __name__ == "__main__":
    send_notifications()

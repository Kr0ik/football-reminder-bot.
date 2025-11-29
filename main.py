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

def get_match_details(row_cells, year_from_url=None):
    """
    Извлекает данные из ячеек строки таблицы.
    Возвращает: datetime_msk, match_title
    """
    try:
        # 1. Дата и время (1-я колонка)
        # Формат обычно: "30.11.2025 | 15:00" или "30.11.2025\n15:00"
        date_text = row_cells[0].get_text(strip=True)
        # Ищем паттерн ДД.ММ.ГГГГ и ЧЧ:ММ
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4}).*?(\d{2}:\d{2})', date_text)
        
        if not date_match:
            return None, None

        day, month, year, time = date_match.groups()
        dt_msk = datetime.strptime(f"{day}.{month}.{year} {time}", "%d.%m.%Y %H:%M")

        # 2. Название матча (обычно в колонке "Счет" - это ссылка)
        # Структура sports.ru: Дата | Турнир | Соперник | Счет/Превью
        # Иногда колонок 5, иногда 4. Счет/Ссылка обычно предпоследняя или последняя.
        
        match_title = ""
        
        # Ищем ячейку со счетом/ссылкой (обычно содержит "превью" или "- : -")
        score_cell = None
        for cell in row_cells:
            if '- : -' in cell.get_text() or 'превью' in cell.get_text().lower() or ':' in cell.get_text():
                 score_cell = cell
                 
        # Если не нашли явную ячейку счета, берем последнюю
        if not score_cell:
            score_cell = row_cells[-1]

        # Пытаемся достать текст ссылки (там обычно "Команда А – Команда Б")
        link = score_cell.find('a')
        if link:
            match_title = link.get_text(strip=True)
        
        # Если ссылки нет или текст пустой, формируем из названия соперника
        if not match_title or match_title == "- : -":
            # Обычно соперник в 3-й колонке (индекс 2)
            opponent = row_cells[2].get_text(strip=True)
            match_title = f"vs {opponent}"

        # Очистка названия от мусора (счета типа "- : -")
        match_title = match_title.replace("- : -", "").strip()
        
        return dt_msk, match_title

    except Exception as e:
        print(f"Error parsing row: {e}")
        return None, None

def get_upcoming_matches(url, team_name):
    print(f"Загрузка {team_name}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        matches = []
        today = datetime.now()
        week_later = today + timedelta(days=7)

        # Ищем таблицу со статистикой (стандарт sports.ru)
        table = soup.find('table', class_='stat-table')
        if not table:
            # Fallback: ищем любую таблицу
            table = soup.find('table')

        if not table:
            return []

        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 4: 
                continue # Пропускаем заголовки
            
            # Проверяем, есть ли признак будущего матча в строке
            row_text = row.get_text().lower()
            is_upcoming = ('- : -' in row_text) or ('превью' in row_text)
            
            if not is_upcoming:
                continue

            dt_msk, match_title = get_match_details(cells)
            
            if dt_msk:
                # Фильтр на 7 дней
                if today <= dt_msk <= week_later:
                    
                    # КОНВЕРТАЦИЯ ВРЕМЕНИ (Москва UTC+3 -> Израиль UTC+2 зимой)
                    # Вычитаем 1 час из datetime объекта
                    # Это автоматически поправит дату, если время было 00:30
                    dt_il = dt_msk - timedelta(hours=1)
                    
                    # Форматирование
                    # Месяцы вручную, чтобы не зависеть от локали сервера
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

        return matches
    except Exception as e:
        print(f"Error fetching {team_name}: {e}")
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
    
    # Отправка с parse_mode='HTML' для жирного текста
    try:
        bot.send_message(CHAT_ID, text, parse_mode='HTML', disable_web_page_preview=True)
        print("Сообщение отправлено!")
    except Exception as e:
        print(f"Ошибка отправки Telegram: {e}")

if __name__ == "__main__":
    send_notifications()

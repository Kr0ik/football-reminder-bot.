import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Days of week in Russian
DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9"
}

def convert_to_jerusalem_time(time_str):
    """Convert Moscow time (UTC+3) to Jerusalem time (UTC+2 in winter)"""
    try:
        time_str = time_str.replace('.', ':')
        if ':' in time_str:
            hours, minutes = map(int, time_str.split(':'))
            hours = hours - 1  # Moscow UTC+3 to Jerusalem UTC+2 (winter)
            if hours < 0:
                hours = 23
            return f"{hours:02d}:{minutes:02d}"
    except:
        pass
    return time_str

def find_matches_for_week():
    """Find matches for next 7 days"""
    manu_matches = []
    cska_matches = []
    
    for day_offset in range(8):
        check_date = datetime.now() + timedelta(days=day_offset)
        date_str = check_date.strftime("%Y-%m-%d")
        day_name = DAYS_RU[check_date.weekday()]
        formatted_date = check_date.strftime("%d.%m.%Y")
        
        url = f"https://www.championat.com/stat/#{date_str}"
        
        try:
            resp = requests.get("https://www.championat.com/stat/", headers=HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            html_lower = resp.text.lower()
            
            # Search for Manchester United
            manu_patterns = ["манчестер юнайтед", "манчестер ю."]
            for pattern in manu_patterns:
                if pattern in html_lower:
                    # Find all lines with time and match info
                    matches = re.findall(r'(\d{1,2}[:\.:]\d{2})\s*([^<]{10,100}' + re.escape(pattern) + r'[^<]{0,50})', html_lower)
                    matches += re.findall(r'(\d{1,2}[:\.:]\d{2})\s*([^<]{0,50}' + re.escape(pattern) + r'[^<]{10,100})', html_lower)
                    
                    for time_str, match_text in matches:
                        jerusalem_time = convert_to_jerusalem_time(time_str)
                        clean_match = ' '.join(match_text.split())[:100]
                        entry = f"📅 {formatted_date} ({day_name})\n⏰ {jerusalem_time} (Иерусалим)\n⚽ {clean_match.title()}"
                        if entry not in manu_matches and "манчестер" in entry.lower():
                            manu_matches.append(entry)
            
            # Search for CSKA Moscow only (in context of Russian league)
            # Look for CSKA in Russian Premier League section
            if "российская премьер-лига" in html_lower or "мир российская" in html_lower:
                # Only CSKA in Russian league context
                cska_pattern = r'(\d{1,2}[:\.:]\d{2})\s*([^<]{0,50}цска[^<]{0,50})'
                matches = re.findall(cska_pattern, html_lower)
                
                for time_str, match_text in matches:
                    # Exclude other CSKAs (Sofia, etc)
                    if 'софия' in match_text.lower() or 'болгар' in match_text.lower():
                        continue
                    jerusalem_time = convert_to_jerusalem_time(time_str)
                    clean_match = ' '.join(match_text.split())[:100]
                    entry = f"📅 {formatted_date} ({day_name})\n⏰ {jerusalem_time} (Иерусалим)\n⚽ {clean_match.title()}"
                    if entry not in cska_matches:
                        cska_matches.append(entry)
            
            break  # Page contains all days
            
        except Exception as e:
            continue
    
    return manu_matches[:5], cska_matches[:5]

def send_notifications():
    manu_matches, cska_matches = find_matches_for_week()
    
    text_parts = ["🏆 Напоминание о матчах на неделю:\n"]
    
    if manu_matches:
        text_parts.append("\n🔴 Манчестер Юнайтед:\n")
        text_parts.extend([f"\n{m}\n" for m in manu_matches])
    else:
        text_parts.append("\n🔴 Манчестер Юнайтед: нет матчей на этой неделе\n")
    
    if cska_matches:
        text_parts.append("\n🔵 ЦСКА Москва:\n")
        text_parts.extend([f"\n{m}\n" for m in cska_matches])
    else:
        text_parts.append("\n🔵 ЦСКА Москва: нет матчей на этой неделе\n")
    
    text_parts.append("\n🔗 https://www.championat.com/stat/")
    
    text = ''.join(text_parts)
    bot.send_message(CHAT_ID, text)

if __name__ == "__main__":
    send_notifications()

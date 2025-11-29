import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Teams to track
MANU_KEYWORDS = ["манчестер юнайтед", "manchester united", "ман юнайтед", "манчестер ю."]
CSKA_KEYWORDS = ["цска"]

# Days of week in Russian
DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def convert_to_jerusalem_time(time_str):
    """Convert Moscow time (UTC+3) to Jerusalem time (UTC+2 winter / UTC+3 summer)"""
    # championat.com shows Moscow time (UTC+3)
    # Jerusalem is UTC+2 in winter, UTC+3 in summer
    # For simplicity, assuming same timezone (both UTC+3 in summer, 1 hour diff in winter)
    # In late November, Israel is on winter time (UTC+2), Moscow is UTC+3
    # So we subtract 1 hour
    try:
        if ':' in time_str:
            hours, minutes = map(int, time_str.replace('.', ':').split(':'))
            # Subtract 1 hour for winter time difference
            hours = hours - 1
            if hours < 0:
                hours = 23
            return f"{hours:02d}:{minutes:02d}"
    except:
        pass
    return time_str

def find_matches_for_week():
    """Find matches for the next 7 days"""
    base_url = "https://www.championat.com/stat/"
    manu_matches = []
    cska_matches = []
    
    # Check next 7 days
    for day_offset in range(8):
        check_date = datetime.now() + timedelta(days=day_offset)
        date_str = check_date.strftime("%Y-%m-%d")
        day_name = DAYS_RU[check_date.weekday()]
        formatted_date = check_date.strftime("%d.%m.%Y")
        
        url = f"{base_url}#{date_str}"
        
        try:
            resp = requests.get(base_url, headers=HEADERS, timeout=20, params={'date': date_str})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Get all text and search for matches
            all_text = soup.get_text(separator='\n')
            lines = all_text.split('\n')
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                # Check for Manchester United
                if any(kw in line_lower for kw in MANU_KEYWORDS):
                    # Look for time in nearby lines
                    time_str = ""
                    match_info = line.strip()
                    
                    # Check surrounding lines for time
                    for j in range(max(0, i-3), min(len(lines), i+3)):
                        time_match = re.search(r'(\d{1,2}[:\.]\d{2})', lines[j])
                        if time_match:
                            time_str = convert_to_jerusalem_time(time_match.group(1))
                            break
                    
                    # Get match context
                    context_lines = []
                    for j in range(max(0, i-1), min(len(lines), i+2)):
                        if lines[j].strip() and len(lines[j].strip()) > 3:
                            context_lines.append(lines[j].strip())
                    
                    match_text = ' '.join(context_lines)[:150]
                    
                    if match_text and time_str:
                        entry = f"📅 {formatted_date} ({day_name})\n⏰ {time_str} (Иерусалим)\n⚽ {match_text}"
                        if entry not in manu_matches:
                            manu_matches.append(entry)
                
                # Check for CSKA
                if any(kw in line_lower for kw in CSKA_KEYWORDS):
                    time_str = ""
                    match_info = line.strip()
                    
                    for j in range(max(0, i-3), min(len(lines), i+3)):
                        time_match = re.search(r'(\d{1,2}[:\.]\d{2})', lines[j])
                        if time_match:
                            time_str = convert_to_jerusalem_time(time_match.group(1))
                            break
                    
                    context_lines = []
                    for j in range(max(0, i-1), min(len(lines), i+2)):
                        if lines[j].strip() and len(lines[j].strip()) > 3:
                            context_lines.append(lines[j].strip())
                    
                    match_text = ' '.join(context_lines)[:150]
                    
                    if match_text and time_str:
                        entry = f"📅 {formatted_date} ({day_name})\n⏰ {time_str} (Иерусалим)\n⚽ {match_text}"
                        if entry not in cska_matches:
                            cska_matches.append(entry)
            
        except Exception as e:
            continue
    
    return manu_matches[:5], cska_matches[:5]  # Limit to 5 matches per team

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

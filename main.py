import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# URLs for team calendars on sports.ru
MANU_URL = "https://www.sports.ru/football/club/mu/calendar/"
CSKA_URL = "https://www.sports.ru/football/club/cska/calendar/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9"
}

def convert_to_jerusalem_time(time_str):
    """Convert Moscow time (UTC+3) to Jerusalem time (UTC+2 in winter)"""
    try:
        time_str = time_str.replace('.', ':').strip()
        if ':' in time_str:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            hours = hours - 1  # Moscow UTC+3 to Jerusalem UTC+2 (winter)
            if hours < 0:
                hours = 23
            return f"{hours:02d}:{minutes:02d}"
    except:
        pass
    return time_str

def get_upcoming_matches(url, team_name):
    """Get upcoming matches from sports.ru calendar page"""
    matches = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find match blocks - looking for upcoming matches (no score yet)
        # Format on sports.ru: date time, teams, league
        text = soup.get_text(separator='\n')
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for date patterns like "30 ноября" or "07 декабря"
            date_match = re.search(r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{1,2}:\d{2})', line)
            
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                time_msk = date_match.group(3)
                time_jer = convert_to_jerusalem_time(time_msk)
                
                # Look for match info in nearby lines
                match_info = ""
                for j in range(max(0, i-2), min(len(lines), i+5)):
                    check_line = lines[j].strip()
                    if ('–' in check_line or '-' in check_line) and 'лига' not in check_line.lower():
                        if len(check_line) > 5 and len(check_line) < 100:
                            match_info = check_line
                            break
                
                if match_info:
                    # Check if match is not completed (no score like "2 0" or "2:0")
                    if not re.search(r'\d\s*[:–-]?\s*\d\s*$', match_info) or 'заверш' not in line.lower():
                        entry = f"📅 {day} {month}\n⏰ {time_jer} (Иерусалим)\n⚽ {match_info}"
                        if entry not in matches:
                            matches.append(entry)
        
        # Also try to find future matches by looking for specific patterns
        # Pattern: "Team1 – Team2" followed by date
        all_text = soup.get_text()
        
        # Find patterns like "30 ноября 15:00"
        future_matches = re.findall(r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{1,2}:\d{2})\s*([^\n]{10,80})', all_text)
        
        for day, month, time_msk, match_text in future_matches:
            if 'заверш' not in match_text.lower():
                time_jer = convert_to_jerusalem_time(time_msk)
                entry = f"📅 {day} {month}\n⏰ {time_jer} (Иерусалим)\n⚽ {match_text.strip()}"
                if entry not in matches and team_name.lower() in entry.lower():
                    matches.append(entry)
        
    except Exception as e:
        matches.append(f"Ошибка: {str(e)[:50]}")
    
    return matches[:5]

def send_notifications():
    manu_matches = get_upcoming_matches(MANU_URL, "Манчестер")
    cska_matches = get_upcoming_matches(CSKA_URL, "ЦСКА")
    
    text_parts = ["🏆 Напоминание о матчах на неделю:\n"]
    
    text_parts.append("\n🔴 Манчестер Юнайтед:\n")
    if manu_matches:
        text_parts.extend([f"{m}\n" for m in manu_matches])
    else:
        text_parts.append("Нет матчей на этой неделе\n")
    
    text_parts.append("\n🔵 ЦСКА Москва:\n")
    if cska_matches:
        text_parts.extend([f"{m}\n" for m in cska_matches])
    else:
        text_parts.append("Нет матчей на этой неделе\n")
    
    text_parts.append("\n🔗 sports.ru")
    
    text = ''.join(text_parts)
    print(text)
    bot.send_message(CHAT_ID, text)
if __name__ == "__main__":
    send_notifications()

import os
import requests
from bs4 import BeautifulSoup
import telebot
import re

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)

MANU_NAMES = ["Манчестер Юнайтед", "Manchester United", "Ман Юнайтед"]
CSKA_NAMES = ["ЦСКА", "CSKA", "ЦСКА Москва"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_team_matches(team_url, team_name):
    """Get upcoming matches for a team from championat.com"""
    try:
        resp = requests.get(team_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        matches = []
        # Find match blocks
        match_items = soup.find_all('div', class_=re.compile(r'match-item|game-item|event-item'))
        
        for item in match_items[:5]:  # Check first 5 matches
            text = item.get_text(separator=' ', strip=True)
            if any(name.lower() in text.lower() for name in [team_name]):
                # Try to find date and time
                date_elem = item.find(class_=re.compile(r'date|time|when'))
                if date_elem:
                    matches.append(f"{team_name}: {date_elem.get_text(strip=True)}")
        
        return matches
    except Exception as e:
        return []

def find_matches():
    """Search for matches on championat.com stat page"""
    url = "https://www.championat.com/stat/"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        
        results = []
        
        # Check for Manchester United
        manu_found = any(name in html for name in MANU_NAMES)
        if manu_found:
            # Try to find specific match info
            match_info = "Манчестер Юнайтед"
            # Search for date/time near team name
            for tag in soup.find_all(string=re.compile(r'Манчестер|Ман Юнайтед|Manchester', re.I)):
                parent = tag.find_parent(['div', 'tr', 'li', 'a'])
                if parent:
                    full_text = parent.get_text(separator=' ', strip=True)
                    if len(full_text) < 200:
                        match_info = full_text
                        break
            results.append(f"⚽ Манчестер Юнайтед:\n{match_info}\nСсылка: https://www.championat.com/football/_england/tournament/6592/calendar/")
        
        # Check for CSKA
        cska_found = any(name in html for name in CSKA_NAMES)
        if cska_found:
            match_info = "ЦСКА Москва"
            for tag in soup.find_all(string=re.compile(r'ЦСКА', re.I)):
                parent = tag.find_parent(['div', 'tr', 'li', 'a'])
                if parent:
                    full_text = parent.get_text(separator=' ', strip=True)
                    if len(full_text) < 200:
                        match_info = full_text
                        break
            results.append(f"⚽ ЦСКА Москва:\n{match_info}\nСсылка: https://www.championat.com/football/_russiapl/tournament/6594/calendar/")
        
        return results
    except Exception as e:
        return [f"Ошибка при получении данных: {str(e)}"]

def send_notifications():
    matches = find_matches()
    if not matches:
        bot.send_message(CHAT_ID, "Нет ближайших матчей Манчестер Юнайтед или ЦСКА на этой неделе.")
        return
    text = "📅 Напоминание о матчах:\n\n" + "\n\n".join(matches)
    bot.send_message(CHAT_ID, text)

if __name__ == "__main__":
    send_notifications()

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
MANU_KEYWORDS = ["манчестер юнайтед", "manchester united", "ман юнайтед"]
CSKA_KEYWORDS = ["цска"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_matches_from_match_center():
    """Get matches from championat.com match center for next 7 days"""
    results = []
    base_url = "https://www.championat.com/stat/"
    
    # Check today and next 7 days
    for day_offset in range(8):
        date = datetime.now() + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")
        url = f"{base_url}#{date_str}"
        
        try:
            resp = requests.get(base_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all match rows
            match_rows = soup.find_all(['div', 'tr', 'a'], class_=re.compile(r'match|game|event|stat-results__item'))
            
            for row in match_rows:
                text = row.get_text(separator=' ', strip=True).lower()
                
                # Check for Manchester United
                if any(keyword in text for keyword in MANU_KEYWORDS):
                    match_info = extract_match_info(row, "Манчестер Юнайтед")
                    if match_info and match_info not in results:
                        results.append(match_info)
                
                # Check for CSKA
                if any(keyword in text for keyword in CSKA_KEYWORDS):
                    match_info = extract_match_info(row, "ЦСКА")
                    if match_info and match_info not in results:
                        results.append(match_info)
            
            break  # Only need to fetch once, page has multiple days
            
        except Exception as e:
            continue
    
    return results

def extract_match_info(element, team_name):
    """Extract match info from HTML element"""
    try:
        text = element.get_text(separator=' ', strip=True)
        
        # Try to find time (format: HH:MM)
        time_match = re.search(r'(\d{1,2}[:\.]\d{2})', text)
        time_str = time_match.group(1) if time_match else ""
        
        # Clean up text - remove excessive whitespace
        clean_text = ' '.join(text.split())
        
        if len(clean_text) > 10 and len(clean_text) < 150:
            return f"⚽ {clean_text}"
        
        return None
    except:
        return None

def find_matches():
    """Main function to find matches"""
    url = "https://www.championat.com/stat/"
    results = []
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        html = resp.text.lower()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Get all text blocks that might contain match info
        all_text = soup.get_text(separator='\n')
        lines = all_text.split('\n')
        
        manu_matches = []
        cska_matches = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check for Manchester United
            if any(kw in line_lower for kw in MANU_KEYWORDS):
                # Get context (surrounding lines)
                context = []
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if lines[j].strip():
                        context.append(lines[j].strip())
                match_text = ' '.join(context)
                if len(match_text) > 10 and match_text not in manu_matches:
                    manu_matches.append(match_text[:200])
            
            # Check for CSKA
            if any(kw in line_lower for kw in CSKA_KEYWORDS):
                context = []
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if lines[j].strip():
                        context.append(lines[j].strip())
                match_text = ' '.join(context)
                if len(match_text) > 10 and match_text not in cska_matches:
                    cska_matches.append(match_text[:200])
        
        # Format results
        if manu_matches:
            results.append(f"⚽ Манчестер Юнайтед:\n" + "\n".join(manu_matches[:3]))
        
        if cska_matches:
            results.append(f"⚽ ЦСКА Москва:\n" + "\n".join(cska_matches[:3]))
        
        return results
        
    except Exception as e:
        return [f"Ошибка: {str(e)}"]

def send_notifications():
    matches = find_matches()
    
    if not matches:
        text = "Нет ближайших матчей Манчестер Юнайтед или ЦСКА на этой неделе.\n"
        text += "Проверьте: https://www.championat.com/stat/"
    else:
        text = "📅 Напоминание о матчах (Матч-центр):\n\n"
        text += "\n\n".join(matches)
        text += "\n\n🔗 https://www.championat.com/stat/"
    
    bot.send_message(CHAT_ID, text)

if __name__ == "__main__":
    send_notifications()

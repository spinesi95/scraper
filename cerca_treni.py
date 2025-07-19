import os
import requests
import time
from datetime import datetime, timedelta, time as time_obj
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def send_telegram_message(message):
    """Invia un messaggio a una chat di Telegram."""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("ERRORE: Le variabili d'ambiente TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID non sono impostate.")
        return

    # Funzione per l'escape dei caratteri speciali per la modalità MarkdownV2 di Telegram
    def escape_markdown_v2(text):
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

    # Formattazione del messaggio con escape dei caratteri
    formatted_message = escape_markdown_v2(message)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': formatted_message,
        'parse_mode': 'MarkdownV2'
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Messaggio inviato con successo a Telegram!")
    else:
        print(f"❌ Errore nell'invio del messaggio a Telegram: {response.status_code} - {response.text}")

def get_target_weekdays(start_days, end_days, weekday_to_find):
    """Genera una lista di date per un dato giorno della settimana."""
    dates = []
    today = datetime.today()
    start_date = today + timedelta(days=start_days)
    end_date = today + timedelta(days=end_days)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == weekday_to_find:
            dates.append(current_date.strftime('%d-%m-%Y'))
        current_date += timedelta(days=1)
    
    return dates

def parse_duration(duration_str):
    """Converte una stringa come '3h 10min' in minuti totali."""
    total_minutes = 0
    try:
        if 'h' in duration_str:
            parts = duration_str.split('h')
            total_minutes += int(parts[0]) * 60
            remaining = parts[1]
        else:
            remaining = duration_str
        
        if 'min' in remaining:
            total_minutes += int(remaining.replace('min', '').strip())
    except (ValueError, IndexError):
        return 9999
    return total_minutes

def scrape_results_for_date(driver, search_date, params, start_time_filter, end_time_filter, max_duration_minutes):
    """Esegue lo scraping per una data e restituisce una lista di risultati testuali."""
    results = []
    full_url = f"https://www.lefrecce.it/Channels.Website.WEB/website/auth/handoff?{urllib.parse.urlencode(params)}"
    driver.get(full_url)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "solution"))
        )
        print(f"✅ Risultati trovati per il {search_date}! Applico i filtri...")

        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        train_results = soup.find_all('div', class_='solution')
        
        trains_found_in_range = 0
        for train in train_results:
            time_elements = train.select('div.od-info b')
            duration_element = train.select_one('div.duration strong')

            if len(time_elements) < 2 or not duration_element:
                continue

            departure_time_str = time_elements[0].text.strip()
            arrival_time_str = time_elements[1].text.strip()
            duration_str = duration_element.text.strip()
            
            try:
                current_departure_time = datetime.strptime(departure_time_str, '%H:%M').time()
                duration_in_minutes = parse_duration(duration_str)
            except ValueError:
                continue

            if (start_time_filter <= current_departure_time <= end_time_filter) and (duration_in_minutes <= max_duration_minutes):
                trains_found_in_range += 1
                price_element = train.find('title2', class_='solution-price-size')
                price = price_element.text.strip() if price_element else "N/D"
                results.append(f"  🕒 {departure_time_str} -> {arrival_time_str} ({duration_str}) | Prezzo: a partire da {price}")
        
        if trains_found_in_range == 0:
            results.append("  -> Nessun treno trovato che soddisfi tutti i filtri per questa data.")

    except Exception as e:
        results.append(f"  -> Non è stato possibile caricare i risultati. Errore: {e}")
    
    return results

def main_scraper():
    """Funzione principale che avvia il browser ed esegue le ricerche."""
    print("🤖 Avvio del browser in modalità headless...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # --- 1. RICERCA VENERDÌ (ANDATA) ---
        fridays = get_target_weekdays(50, 120, 4)
        if fridays:
            print("\n" + "#"*20 + " INIZIO RICERCA VENERDÌ (ROMA -> MILANO) " + "#"*20)
            for date in fridays:
                day_report = [f"*🚄 Ricerca Venerdì (Roma -> Milano)*\n*Data: {date}*"]
                params = {
                    'action': 'searchTickets', 'lang': 'it', 'referrer': 'www.trenitalia.com',
                    'tripType': 'on', 'ynFlexibleDates': 'off', 'departureDate': date,
                    'departureStation': 'Roma Termini', 'departureTime': '16',
                    'arrivalStation': 'Milano Centrale', 'selectedTrainType': 'tutti',
                    'noOfChildren': '0', 'noOfAdults': '1',
                }
                results = scrape_results_for_date(driver, date, params, 
                                                  start_time_filter=time_obj(16, 0), 
                                                  end_time_filter=time_obj(18, 30), 
                                                  max_duration_minutes=200)
                day_report.extend(results)
                send_telegram_message("\n".join(day_report))
                time.sleep(1) # Pausa di 1 secondo per non sovraccaricare l'API di Telegram

        # --- 2. RICERCA DOMENICHE (RITORNO) ---
        sundays = get_target_weekdays(50, 120, 6)
        if sundays:
            print("\n" + "#"*20 + " INIZIO RICERCA DOMENICHE (MILANO -> ROMA) " + "#"*20)
            for date in sundays:
                day_report = [f"*🚄 Ricerca Domeniche (Milano -> Roma)*\n*Data: {date}*"]
                params = {
                    'action': 'searchTickets', 'lang': 'it', 'referrer': 'www.trenitalia.com',
                    'tripType': 'on', 'ynFlexibleDates': 'off', 'departureDate': date,
                    'departureStation': 'Milano Centrale', 'departureTime': '14',
                    'arrivalStation': 'Roma Termini', 'selectedTrainType': 'tutti',
                    'noOfChildren': '0', 'noOfAdults': '1',
                }
                results = scrape_results_for_date(driver, date, params

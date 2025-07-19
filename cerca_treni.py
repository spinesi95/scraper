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

def get_target_fridays(start_days, end_days):
    """
    Genera una lista di date (stringhe formattate) per tutti i venerdì
    compresi tra 'start_days' e 'end_days' giorni da oggi.
    """
    fridays = []
    today = datetime.today()
    start_date = today + timedelta(days=start_days)
    end_date = today + timedelta(days=end_days)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 4: # 4 corrisponde a Venerdì
            fridays.append(current_date.strftime('%d-%m-%Y'))
        current_date += timedelta(days=1)
    
    return fridays

def main_scraper():
    """
    Funzione principale che avvia il browser, cicla sulle date target
    ed esegue lo scraping per ciascuna di esse.
    """
    # === IMPOSTAZIONI DI RICERCA ===
    departure_station = 'Roma Termini'
    arrival_station = 'Milano Centrale'
    departure_time_filter = '16' # Cerca a partire da quest'ora
    
    # Filtro sull'orario di partenza
    start_time_filter = time_obj(16, 0)
    end_time_filter = time_obj(18, 30)
    # ===============================

    target_dates = get_target_fridays(50, 120)

    if not target_dates:
        print("Nessun venerdì trovato nell'intervallo di date specificato.")
        return

    print("=" * 60)
    print("🤖 Avvio del browser in modalità headless...")
    
    # Impostazioni di Selenium per la modalità headless
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Itera su ogni venerdì trovato
        for search_date in target_dates:
            print("\n" + "="*60)
            print(f"🔎 Ricerca treni per Venerdì {search_date}")
            print("="*60)

            base_url = "https://www.lefrecce.it/Channels.Website.WEB/website/auth/handoff"
            params = {
                'action': 'searchTickets', 'lang': 'it', 'referrer': 'www.trenitalia.com',
                'tripType': 'on', 'ynFlexibleDates': 'off', 'departureDate': search_date,
                'departureStation': departure_station, 'departureTime': departure_time_filter,
                'arrivalStation': arrival_station, 'selectedTrainType': 'tutti',
                'noOfChildren': '0', 'noOfAdults': '1',
            }
            
            full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
            driver.get(full_url)

            try:
                # Attende che i risultati per la data corrente siano caricati
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "solution"))
                )
                print(f"✅ Risultati trovati per il {search_date}! Applico il filtro (16:00-18:30)...")

                page_html = driver.page_source
                soup = BeautifulSoup(page_html, 'html.parser')
                train_results = soup.find_all('div', class_='solution')
                
                trains_found_in_range = 0
                for train in train_results:
                    time_elements = train.select('div.od-info b')
                    if len(time_elements) >= 2:
                        departure_time_str = time_elements[0].text.strip()
                        arrival_time = time_elements[1].text.strip()
                        
                        try:
                            current_departure_time = datetime.strptime(departure_time_str, '%H:%M').time()
                        except ValueError:
                            continue

                        if start_time_filter <= current_departure_time <= end_time_filter:
                            trains_found_in_range += 1
                            price_element = train.find('title2', class_='solution-price-size')
                            price = price_element.text.strip() if price_element else "N/D"
                            print(f"  🕒 {departure_time_str} -> {arrival_time} | 💵 Prezzo: a partire da {price}")
                
                if trains_found_in_range == 0:
                    print("  -> Nessun treno trovato nell'intervallo di tempo specificato per questa data.")

            except Exception as e:
                print(f"  -> Non è stato possibile caricare i risultati per il {search_date}. Errore: {e}")

    finally:
        print("\n" + "="*60)
        print("Ricerca completata. Chiusura del browser.")
        driver.quit()

if __name__ == "__main__":
    main_scraper()

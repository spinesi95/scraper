import time
from datetime import datetime, timedelta
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def find_next_friday():
    """Trova la data del prossimo venerdì nel formato corretto (GG-MM-AAAA)."""
    today = datetime.today()
    days_ahead = (4 - today.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_friday = today + timedelta(days=days_ahead)
    return next_friday.strftime('%d-%m-%Y')

def search_and_print_tickets():
    """
    Usa Selenium in modalità headless per caricare la pagina dinamicamente
    e BeautifulSoup per estrarre i dati.
    """
    search_date = find_next_friday()
    
    base_url = "https://www.lefrecce.it/Channels.Website.WEB/website/auth/handoff"
    params = {
        'action': 'searchTickets', 'lang': 'it', 'referrer': 'www.trenitalia.com',
        'tripType': 'on', 'ynFlexibleDates': 'off', 'departureDate': search_date,
        'departureStation': 'Roma Termini', 'departureTime': '16',
        'arrivalStation': 'Milano Centrale', 'selectedTrainType': 'tutti',
        'noOfChildren': '0', 'noOfAdults': '1',
    }
    
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    print("=" * 60)
    print(f"Ricerca treni per il {search_date} da Roma Termini a Milano Centrale")
    print("🤖 Avvio del browser in modalità headless...")
    print("=" * 60)

    # === MODIFICHE PER GITHUB ACTIONS ===
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") # Esegui senza interfaccia grafica
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080") # Imposta una dimensione della finestra
    # ====================================
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(full_url)

        print("Pagina caricata. Attendo i risultati del viaggio...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "solution"))
        )
        print("✅ Risultati trovati!\n")
        
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        
        train_results = soup.find_all('div', class_='solution')

        if not train_results:
            print("❌ Nessun risultato trovato.")
            return

        print(f"Trovati {len(train_results)} treni:\n")

        for train in train_results:
            time_elements = train.select('div.od-info b')
            if len(time_elements) >= 2:
                departure_time = time_elements[0].text.strip()
                arrival_time = time_elements[1].text.strip()
            else:
                departure_time, arrival_time = "N/D", "N/D"

            price_element = train.find('title2', class_='solution-price-size')
            price = price_element.text.strip() if price_element else "N/D"

            print(f"🕒 Partenza: {departure_time} -> Arrivo: {arrival_time} | 💵 Prezzo: a partire da {price}")

    except Exception as e:
        print(f"Si è verificato un errore: {e}")
    finally:
        print("\nChiusura del browser.")
        driver.quit()

if __name__ == "__main__":
    search_and_print_tickets()

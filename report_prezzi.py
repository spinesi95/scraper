import requests
from bs4 import BeautifulSoup
import os
import re
import time
from datetime import datetime

# ==========================================
#              CONFIGURAZIONE
# ==========================================

# Recupero credenziali (GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- LISTA DATE DA CONTROLLARE ---
# Inserisci qui tutte le date che vuoi (formato AAAA-MM-GG)
DATE_DA_CONTROLLARE = [
    "2026-01-19",  # Lunedì
    "2026-01-20"   # Martedì
]

SOGLIA_PREZZO = 100.0        # Avvisa se trova biglietti SOTTO questa cifra

# ==========================================

def invia_telegram(testo):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(" [!] Errore: Token o Chat ID mancanti.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID, 
        'text': testo,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f" [X] Errore Telegram: {response.text}")
        else:
            print(" [v] Notifica inviata.")
    except Exception as e:
        print(f" [!] Errore connessione: {e}")

def pulisci_prezzo(prezzo_str):
    try:
        clean = re.sub(r'[^\d.,]', '', prezzo_str).replace(',', '.')
        return float(clean)
    except:
        return 999.9

def controlla_singola_data(data_str):
    """Esegue il controllo per una data specifica"""
    
    # Genera l'URL specifico per questa data
    url_corrente = f"https://trovaunposto.it/trains/searchTrainTicket?departure=MILANO%28TUTTE+LE+STAZIONI%29&arrival=ROMA%28TUTTE+LE+STAZIONI%29&date={data_str}"
    
    print(f"--- Controllo {data_str} ---")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url_corrente, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            print(f" [!] Sito irraggiungibile per {data_str} (Status: {resp.status_code})")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        biglietti = soup.find_all('div', class_='ticket-info showing')
        
        messaggi_treni = []
        
        for ticket in biglietti:
            try:
                orario_raw = ticket.find('div', class_='time').text.strip()
                orario = " ".join(orario_raw.split())
                
                prezzo_txt = ticket.find('div', class_='mob-right').text.strip()
                prezzo_val = pulisci_prezzo(prezzo_txt)
                
                if prezzo_val <= SOGLIA_PREZZO:
                    messaggi_treni.append(f"🚄 {orario}  |  💰 <b>{prezzo_txt}</b>")
            except:
                continue

        if messaggi_treni:
            print(f" [!!!] Trovate {len(messaggi_treni)} offerte per il {data_str}!")
            
            # Formattazione data (es. 19/01/2026)
            data_human = datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            testo = (f"📅 <b>OFFERTE DEL {data_human}</b>\n"
                     f"🔔 Soglia: {SOGLIA_PREZZO}€\n\n")
            
            testo += "\n".join(messaggi_treni[:10])
            testo += f"\n\n👉 <a href='{url_corrente}'>Prenota biglietti</a>"
            
            invia_telegram(testo)
        else:
            print(f" [i] Nessuna offerta interessante per il {data_str}.")

    except Exception as e:
        print(f" [!] Errore durante il controllo di {data_str}: {e}")

def job_principale():
    print(f"=== AVVIO CICLO MULTI-DATA ===")
    
    for data in DATE_DA_CONTROLLARE:
        controlla_singola_data(data)
        # Pausa di 5 secondi tra una data e l'altra per educazione verso il server
        time.sleep(5)
        
    print("=== FINE CICLO ===")

if __name__ == "__main__":
    job_principale()

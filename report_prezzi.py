import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime

# ==========================================
#              CONFIGURAZIONE
# ==========================================

# Se sei su GitHub, legge i Secrets. 
# Se sei sul PC, puoi sostituire os.environ.get(...) con la tua stringa tra virgolette.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Impostazioni Viaggio
DATA_TARGET = "2026-01-19"  
SOGLIA_PREZZO = 70.0        # <--- SOTTO questa cifra invia il messaggio. SOPRA sta zitto.
URL_MI_RM = f"https://trovaunposto.it/trains/searchTrainTicket?departure=MILANO%28TUTTE+LE+STAZIONI%29&arrival=ROMA%28TUTTE+LE+STAZIONI%29&date={DATA_TARGET}"

# ==========================================

def invia_telegram(testo):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(" [!] Errore: Token o Chat ID mancanti.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID, 
        'text': testo,
        'parse_mode': 'HTML',            # Attiva grassetto e link
        'disable_web_page_preview': True # Rimuove l'anteprima del sito per pulizia
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print(" [v] Notifica inviata con successo!")
        else:
            print(f" [X] Errore Telegram: {response.text}")
    except Exception as e:
        print(f" [!] Errore connessione: {e}")

def pulisci_prezzo(prezzo_str):
    try:
        # Trasforma "39.90 €" in 39.90
        clean = re.sub(r'[^\d.,]', '', prezzo_str).replace(',', '.')
        return float(clean)
    except:
        return 999.9

def esegui_controllo():
    print(f"--- AVVIO CONTROLLO: {DATA_TARGET} (Soglia: {SOGLIA_PREZZO}€) ---")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(URL_MI_RM, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            print(f" [!] Sito irraggiungibile: {resp.status_code}")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        biglietti = soup.find_all('div', class_='ticket-info showing')
        
        messaggi_treni = []
        
        for ticket in biglietti:
            try:
                # Estrazione dati
                orario_raw = ticket.find('div', class_='time').text.strip()
                orario = " ".join(orario_raw.split()) # Toglie spazi extra
                
                prezzo_txt = ticket.find('div', class_='mob-right').text.strip()
                prezzo_val = pulisci_prezzo(prezzo_txt)
                
                # --- IL FILTRO MAGICO ---
                # Se il prezzo è BASSO, lo aggiunge alla lista.
                # Se è ALTO, lo ignora completamente.
                if prezzo_val <= SOGLIA_PREZZO:
                    messaggi_treni.append(f"🚄 {orario}  |  💰 <b>{prezzo_txt}</b>")
            except:
                continue

        # --- DECISIONE FINALE ---
        if messaggi_treni:
            print(f" [!!!] Trovati {len(messaggi_treni)} treni sotto soglia. INVIO NOTIFICA.")
            
            # Conversione data per estetica (da 2026-01-19 a 19/01/2026)
            data_human = datetime.strptime(DATA_TARGET, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            testo = (f"📅 <b>OFFERTE DEL {data_human}</b>\n"
                     f"🔔 Soglia: {SOGLIA_PREZZO}€\n\n")
            
            testo += "\n".join(messaggi_treni[:10]) # Max 10 treni per non intasare
            testo += f"\n\n👉 <a href='{URL_MI_RM}'>Clicca qui per prenotare</a>"
            
            invia_telegram(testo)
        else:
            # Se la lista è vuota, stampa solo su console e NON manda nulla su Telegram
            print(" [i] Nessun biglietto interessante trovato. Bot silenzioso.")

    except Exception as e:
        print(f" [!] Errore script: {e}")

if __name__ == "__main__":
    esegui_controllo()

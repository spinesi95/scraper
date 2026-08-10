import requests
import os
import time
from datetime import datetime

# ==========================================
#            CONFIGURAZIONE
# ==========================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

DATE_DA_CONTROLLARE = ["27/11/2026", "28/11/2026"]
PICKUP_RICHIESTO = "08:30"
EXCURSION_ID = "1"

FILE_MEMORIA = "ultima_notifica.txt"

# ==========================================
#               FUNZIONI
# ==========================================

def gia_notificato_oggi():
    """Controlla se abbiamo già inviato una notifica oggi."""
    oggi = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(FILE_MEMORIA):
        with open(FILE_MEMORIA, "r") as f:
            data_salvata = f.read().strip()
            if data_salvata == oggi:
                return True
    return False

def salva_notifica_oggi():
    """Salva la data odierna per non inviare più notifiche fino a domani."""
    oggi = datetime.now().strftime("%Y-%m-%d")
    with open(FILE_MEMORIA, "w") as f:
        f.write(oggi)

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
        if response.status_code == 200:
            print(" [v] Notifica Telegram inviata con successo.")
        else:
            print(f" [X] Errore Telegram: {response.text}")
    except Exception as e:
        print(f" [!] Errore connessione Telegram: {e}")

def controlla_singola_data(data_str):
    """Controlla una data e restituisce il testo dei posti trovati (o None)"""
    url_corrente = f"https://api.hieloyaventura.com/api/hya/shifts?date_from={data_str}&date_to={data_str}&excursion_id={EXCURSION_ID}"
    print(f"--- Controllo {data_str} ---")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url_corrente, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None

        dati_json = resp.json()
        turni = dati_json.get("TURNOS", [])
        
        messaggi_escursione = []
        for turno in turni:
            if turno.get("PICKUP", "") == PICKUP_RICHIESTO:
                posti_totali = int(turno.get("TOD", 0)) + int(turno.get("TRD", 0))
                
                if posti_totali > 0:
                    messaggi_escursione.append(
                        f"📅 <b>Data:</b> {data_str}\n"
                        f"🕒 <b>Turno:</b> {turno.get('TURNO', '')} (Pickup {PICKUP_RICHIESTO})\n"
                        f"🎟 <b>Posti disponibili:</b> {posti_totali}\n"
                        f"💰 <b>Prezzo:</b> {turno.get('VALOR_TOTAL', '0')}"
                    )

        if messaggi_escursione:
            return "\n\n".join(messaggi_escursione)
            
    except Exception as e:
        print(f" [!] Errore su {data_str}: {e}")
        
    return None

def job_principale():
    print("=== AVVIO CONTROLLO DISPONIBILITÀ ===")
    
    if gia_notificato_oggi():
        print(" [i] Notifica già inviata oggi. Salto il controllo per evitare spam.")
        return

    messaggi_trovati = []
    
    for data in DATE_DA_CONTROLLARE:
        risultato = controlla_singola_data(data)
        if risultato:
            messaggi_trovati.append(risultato)
        time.sleep(2)
        
    if messaggi_trovati:
        print(" [!!!] Posti trovati! Preparo la notifica...")
        testo_finale = "🧊 <b>HIELO Y AVENTURA - DISPONIBILITÀ!</b>\n\n"
        testo_finale += "\n\n---\n\n".join(messaggi_trovati)
        testo_finale += "\n\n👉 <a href='https://hieloyaventura.com/'>Vai al sito ufficiale</a>"
        
        invia_telegram(testo_finale)
        salva_notifica_oggi()
    else:
        print(" [i] Nessun posto disponibile ai requisiti richiesti.")

if __name__ == "__main__":
    job_principale()

import requests
import os
import time

# ==========================================
#            CONFIGURAZIONE
# ==========================================

# Recupero credenziali (GitHub Secrets o variabili d'ambiente)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- LISTA DATE DA CONTROLLARE ---
# Formato richiesto dall'API: GG/MM/AAAA
DATE_DA_CONTROLLARE = [
    "26/11/2026",
    "27/11/2026"
]

PICKUP_RICHIESTO = "08:30"
EXCURSION_ID = "1"

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
        print(f" [!] Errore connessione Telegram: {e}")

def controlla_singola_data(data_str):
    """Esegue il controllo per una data specifica"""
    
    # L'API accetta date_from e date_to. Usiamo la stessa data per controllare un giorno alla volta.
    url_corrente = f"https://api.hieloyaventura.com/api/hya/shifts?date_from={data_str}&date_to={data_str}&excursion_id={EXCURSION_ID}"
    
    print(f"--- Controllo {data_str} ---")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url_corrente, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            print(f" [!] API irraggiungibile per {data_str} (Status: {resp.status_code})")
            return

        # Parsing diretto del JSON
        dati_json = resp.json()
        turni = dati_json.get("TURNOS", [])
        prodotto = dati_json.get("PRODUCTOD", "Escursione")
        
        messaggi_escursione = []
        
        for turno in turni:
            pickup = turno.get("PICKUP", "")
            
            # Filtriamo solo i turni con il pickup desiderato
            if pickup == PICKUP_RICHIESTO:
                # Nel JSON i posti sembrano divisi in TOD e TRD. Li sommiamo per sicurezza.
                posti_tod = int(turno.get("TOD", 0))
                posti_trd = int(turno.get("TRD", 0))
                posti_totali = posti_tod + posti_trd
                
                orario_turno = turno.get("TURNO", "")
                prezzo = turno.get("VALOR_TOTAL", "0")
                
                if posti_totali > 0:
                    messaggi_escursione.append(
                        f"🕒 <b>Turno: {orario_turno}</b> (Pickup: {pickup})\n"
                        f"🎟 Posti disponibili: <b>{posti_totali}</b>\n"
                        f"💰 Prezzo totale: <b>{prezzo}</b>"
                    )

        if messaggi_escursione:
            print(f" [!!!] Trovati posti per il {data_str}!")
            
            testo = (f"🧊 <b>{prodotto} - DISPONIBILITÀ TROVATA</b>\n"
                     f"📅 Data: {data_str}\n\n")
            
            testo += "\n\n".join(messaggi_escursione)
            testo += f"\n\n👉 <a href='https://hieloyaventura.com/'>Vai al sito ufficiale</a>"
            
            invia_telegram(testo)
        else:
            print(f" [i] Nessun posto disponibile per il {data_str} con pickup alle {PICKUP_RICHIESTO}.")

    except Exception as e:
        print(f" [!] Errore durante il controllo di {data_str}: {e}")

def job_principale():
    print(f"=== AVVIO CICLO MULTI-DATA ===")
    
    for data in DATE_DA_CONTROLLARE:
        controlla_singola_data(data)
        # Pausa di 2 secondi tra una chiamata e l'altra per educazione verso il server
        time.sleep(2)
        
    print("=== FINE CICLO ===")

if __name__ == "__main__":
    job_principale()

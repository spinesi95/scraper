import requests
import os
import time
import json
from datetime import datetime, timedelta

# ==========================================
#            CONFIGURAZIONE
# ==========================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

DATE_DA_CONTROLLARE = ["27/11/2026", "28/11/2026"]
PICKUP_RICHIESTO = "08:30"
EXCURSION_ID = "1"

FILE_STATO = "stato.json"
DIR_STORICO = "storico"

# ==========================================
#               FUNZIONI
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
        if response.status_code == 200:
            print(" [v] Notifica Telegram inviata con successo.")
        else:
            print(f" [X] Errore Telegram: {response.text}")
    except Exception as e:
        print(f" [!] Errore connessione Telegram: {e}")

def salva_storico_6_mesi():
    """Scarica il JSON da oggi a +6 mesi e lo salva nella cartella storico/"""
    os.makedirs(DIR_STORICO, exist_ok=True)
    
    oggi = datetime.now()
    tra_6_mesi = oggi + timedelta(days=180)
    
    date_from = oggi.strftime("%d/%m/%Y")
    date_to = tra_6_mesi.strftime("%d/%m/%Y")
    
    url = f"https://api.hieloyaventura.com/api/hya/shifts?date_from={date_from}&date_to={date_to}&excursion_id={EXCURSION_ID}"
    print(f"--- Salvataggio storico ({date_from} - {date_to}) ---")
    
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        if resp.status_code == 200:
            nome_file = f"calendario_{oggi.strftime('%Y-%m-%d')}.json"
            percorso = os.path.join(DIR_STORICO, nome_file)
            
            with open(percorso, "w") as f:
                # Salviamo il JSON compatto per risparmiare spazio
                json.dump(resp.json(), f)
            print(f" [v] File storico salvato in {percorso}")
        else:
            print(f" [X] Errore API storico: {resp.status_code}")
    except Exception as e:
        print(f" [!] Errore salvataggio storico: {e}")

def controlla_singola_data(data_str):
    """Restituisce: (testo_formattato, quantita_totale_posti)"""
    url_corrente = f"https://api.hieloyaventura.com/api/hya/shifts?date_from={data_str}&date_to={data_str}&excursion_id={EXCURSION_ID}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url_corrente, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None, 0

        turni = resp.json().get("TURNOS", [])
        
        messaggi_escursione = []
        posti_totali_giornata = 0
        
        for turno in turni:
            if turno.get("PICKUP", "") == PICKUP_RICHIESTO:
                posti_turno = int(turno.get("TOD", 0)) + int(turno.get("TRD", 0))
                posti_totali_giornata += posti_turno
                
                if posti_turno > 0:
                    messaggi_escursione.append(
                        f"📅 <b>Data:</b> {data_str}\n"
                        f"🕒 <b>Turno:</b> {turno.get('TURNO', '')} (Pickup {PICKUP_RICHIESTO})\n"
                        f"🎟 <b>Posti disponibili:</b> {posti_turno}\n"
                        f"💰 <b>Prezzo:</b> {turno.get('VALOR_TOTAL', '0')}"
                    )

        if messaggi_escursione:
            return "\n\n".join(messaggi_escursione), posti_totali_giornata
            
    except Exception as e:
        print(f" [!] Errore lettura {data_str}: {e}")
        
    return None, 0

def job_principale():
    print("=== AVVIO SCRIPT ===")
    
    # 1. Salva lo storico dei 6 mesi in background
    salva_storico_6_mesi()
    time.sleep(2)
    
    # 2. Leggi la memoria del bot
    stato_precedente = {"ultima_data": "", "quantita": {}}
    if os.path.exists(FILE_STATO):
        with open(FILE_STATO, "r") as f:
            stato_precedente = json.load(f)
            
    oggi_str = datetime.now().strftime("%Y-%m-%d")
    gia_notificato_oggi = (stato_precedente.get("ultima_data") == oggi_str)
    quantita_precedenti = stato_precedente.get("quantita", {})
    
    # 3. Controlla le disponibilità attuali
    quantita_attuali = {}
    messaggi_trovati = []
    
    for data in DATE_DA_CONTROLLARE:
        print(f"--- Controllo {data} ---")
        risultato_testo, qt_totale = controlla_singola_data(data)
        quantita_attuali[data] = qt_totale
        
        if risultato_testo:
            messaggi_trovati.append(risultato_testo)
        time.sleep(2)

    # 4. Verifica se ci sono state variazioni numeriche rispetto all'ultimo check
    variazione_rilevata = False
    for data in DATE_DA_CONTROLLARE:
        if quantita_attuali.get(data, 0) != quantita_precedenti.get(data, 0):
            variazione_rilevata = True
            break

    # 5. Logica di notifica
    invia_messaggio = False
    titolo = ""
    
    if not gia_notificato_oggi:
        invia_messaggio = True
        titolo = "🧊 <b>REPORT GIORNALIERO HIELO Y AVENTURA</b>\n\n"
        print(" [i] Primo controllo del giorno. Invio report.")
    elif variazione_rilevata:
        invia_messaggio = True
        titolo = "⚠️ <b>VARIAZIONE POSTI RILEVATA!</b>\n\n"
        print(" [!] La quantità di posti è cambiata. Invio avviso!")
    else:
        print(" [i] Report già inviato e nessuna variazione di posti rilevata.")

    # 6. Spedizione Telegram e salvataggio stato
    if invia_messaggio:
        totale_posti_ora = sum(quantita_attuali.values())
        
        if totale_posti_ora > 0:
            testo_finale = titolo + "\n\n---\n\n".join(messaggi_trovati)
            testo_finale += "\n\n👉 <a href='https://hieloyaventura.com/'>Vai al sito ufficiale</a>"
        else:
            testo_finale = titolo + "❌ <b>Nessun posto disponibile</b> al momento per le date richieste."
            
        invia_telegram(testo_finale)
        
        # Salva la nuova memoria
        nuovo_stato = {
            "ultima_data": oggi_str,
            "quantita": quantita_attuali
        }
        with open(FILE_STATO, "w") as f:
            json.dump(nuovo_stato, f, indent=2)

if __name__ == "__main__":
    job_principale()

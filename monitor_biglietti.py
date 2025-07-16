import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime
import time

# Percorso per il disco persistente di Render
RENDER_DATA_DIR = "/var/data"

# --- CONFIGURAZIONE ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('MONITOR_URL')

FILE_DATI = os.path.join(RENDER_DATA_DIR, 'dati_biglietti1.txt')
FILE_TIMESTAMP_NOTIFICA = os.path.join(RENDER_DATA_DIR, 'ultima_notifica1.txt')
ORE_PER_NOTIFICA_ATTIVA = 8
# --- FINE CONFIGURAZIONE ---

def leggi_file(nome_file):
    """Funzione generica per leggere un file."""
    try:
        with open(nome_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def scrivi_file(nome_file, contenuto):
    """Funzione generica per scrivere su un file."""
    with open(nome_file, 'w', encoding='utf-8') as f:
        f.write(str(contenuto))

def invia_messaggio_telegram(messaggio, url_bottone):
    """Invia un messaggio con un bottone inline."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Credenziali Telegram non impostate.")
        return False
    
    tastiera = {'inline_keyboard': [[{'text': '➡️ VAI ALLA PAGINA ⬅️', 'url': url_bottone}]]}
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': messaggio,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps(tastiera)
    }
    url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(url_api, data=payload)
        response.raise_for_status()
        print("Messaggio inviato con successo a Telegram!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Errore durante l'invio del messaggio: {e}")
        return False

def controlla_biglietti():
    """Estrae i dettagli dei biglietti e gestisce le notifiche."""
    if not URL:
        print("Errore: URL di monitoraggio non impostato.")
        return
        
    print(f"Avvio controllo biglietti alle {datetime.now().strftime('%H:%M:%S')}...")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        elementi_biglietti = soup.find_all('div', class_='ticket-info showing')
        
        lista_dettagli = []
        if not elementi_biglietti:
            dati_attuali = "Nessun biglietto disponibile."
        else:
            for ticket in elementi_biglietti:
                orario_el = ticket.find('div', class_='col-20 block time')
                tratta_el = ticket.find('div', class_='col-30 block mobile-pl tra_stat_title')
                prezzo_el = ticket.find('div', class_='col-16 block mob-right')
                orario = " ".join(orario_el.text.strip().split()) if orario_el else "N/D"
                tratta = " ".join(tratta_el.text.strip().split()) if tratta_el else "N/D"
                prezzo = " ".join(prezzo_el.text.strip().split()) if prezzo_el else "N/D"
                lista_dettagli.append(f"• {orario} | {tratta} | <b>{prezzo}</b>")
            dati_attuali = "\n".join(lista_dettagli)
        
        dati_precedenti = leggi_file(FILE_DATI)
        orario_controllo = datetime.now().strftime("%H:%M del %d/%m/%Y")
        
        notifica_da_inviare = False
        messaggio = ""

        if dati_precedenti is None:
            messaggio = f"✅ <b>Monitoraggio avviato</b>\n<i>Controllo delle {orario_controllo}</i>\n\n<b>Biglietti trovati:</b>\n{dati_attuali}"
            notifica_da_inviare = True
        elif dati_attuali != dati_precedenti:
            messaggio = f"❗️<b>Variazione Rilevata!</b>❗️\n<i>Controllo delle {orario_controllo}</i>\n\n<b>Nuovi dati:</b>\n{dati_attuali}"
            notifica_da_inviare = True
        else:
            print("Nessuna variazione rilevata.")
            timestamp_str = leggi_file(FILE_TIMESTAMP_NOTIFICA)
            if timestamp_str:
                secondi_da_ultima_notifica = time.time() - float(timestamp_str)
                if secondi_da_ultima_notifica > (ORE_PER_NOTIFICA_ATTIVA * 3600):
                    messaggio = f"✅ <b>Monitoraggio attivo</b>\n<i>Nessuna variazione da >{ORE_PER_NOTIFICA_ATTIVA} ore (controllo delle {orario_controllo})</i>\n\n<b>Stato attuale:</b>\n{dati_attuali}"
                    notifica_da_inviare = True

        if notifica_da_inviare:
            if invia_messaggio_telegram(messaggio, URL):
                print("Aggiornamento file di stato...")
                scrivi_file(FILE_DATI, dati_attuali)
                scrivi_file(FILE_TIMESTAMP_NOTIFICA, time.time())
                print("File aggiornati con successo.")

    except Exception as e:
        print(f"Si è verificato un errore critico: {e}")
        invia_messaggio_telegram(f"☠️ Errore nello script alle {datetime.now().strftime('%H:%M')}:\n<pre>{e}</pre>", URL)

# --- Punto di ingresso dello script ---
if __name__ == '__main__':
    # ▼▼▼ RIGA AGGIUNTA ▼▼▼
    # Assicura che la cartella per i dati esista prima di provare a usarla
    os.makedirs(RENDER_DATA_DIR, exist_ok=True)
    
    controlla_biglietti()

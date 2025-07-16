import requests
from bs4 import BeautifulSoup
import os
import json 
from datetime import datetime
import time
# --- CONFIGURAZIONE ---
# Le credenziali e l'URL verranno letti dalle "Secrets" di GitHub
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('MONITOR_URL')

# Il file ora salva una "fotografia" testuale dei dati, non solo un numero.
FILE_DATI = 'dati_biglietti.txt'
FILE_TIMESTAMP_NOTIFICA = 'ultima_notifica.txt'
ORE_PER_NOTIFICA_ATTIVA = 8
# --- FINE CONFIGURAZIONE ---

def leggi_dati_precedenti():
    """Legge i dati dei biglietti dall'ultima esecuzione."""
    try:
        with open(FILE_DATI, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

def salva_dati_attuali(dati):
    """Salva i dati dei biglietti correnti su file."""
    with open(FILE_DATI, 'w', encoding='utf-8') as f:
        f.write(dati)

def leggi_timestamp_notifica():
    """Legge il timestamp dell'ultima notifica inviata."""
    try:
        with open(FILE_TIMESTAMP_NOTIFICA, 'r') as f:
            return f.read()
    except (FileNotFoundError, ValueError):
        return None

timestamp_attuale = int(time.time())

def salva_timestamp_notifica():
    """Salva il timestamp attuale dopo aver inviato una notifica."""
    with open(FILE_TIMESTAMP_NOTIFICA, 'w') as f:
        f.write(str(timestamp_attuale))

def invia_messaggio_telegram(messaggio, url_bottone):
    """Invia un messaggio con un bottone inline."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Token o Chat ID di Telegram non impostati.")
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
        return True # Ritorna True se l'invio ha successo
    except requests.exceptions.RequestException as e:
        print(f"Errore durante l'invio del messaggio a Telegram: {e}")
        return False # Ritorna False se l'invio fallisce

def controlla_biglietti():
    """Estrae i dettagli dei biglietti e notifica le variazioni o se sono passate 8 ore."""
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
        
        dati_precedenti = leggi_dati_precedenti()
        orario_controllo = datetime.now().strftime("%H:%M del %d/%m/%Y")
        
        notifica_inviata = False

        if dati_precedenti is None:
            messaggio = f"✅ <b>Monitoraggio avviato</b>\n<i>Controllo delle {orario_controllo}</i>\n\n<b>Biglietti trovati:</b>\n{dati_attuali}"
            if invia_messaggio_telegram(messaggio, URL):
                notifica_inviata = True
        elif dati_attuali != dati_precedenti:
            messaggio = f"❗️<b>Variazione Rilevata!</b>❗️\n<i>Controllo delle {orario_controllo}</i>\n\n<b>Nuovi dati:</b>\n{dati_attuali}"
            if invia_messaggio_telegram(messaggio, URL):
                notifica_inviata = True
        else:
            print("Nessuna variazione rilevata.")
            # Controlla se inviare la notifica "keep-alive"
            timestamp_notifica = leggi_timestamp_notifica()
            if (timestamp_attuale - int(timestamp_notifica)) > (ORE_PER_NOTIFICA_ATTIVA * 3600):
                messaggio = f"✅ <b>Monitoraggio attivo</b>\n<i>Nessuna variazione da >{ORE_PER_NOTIFICA_ATTIVA} ore (controllo delle {orario_controllo})</i>\n\n<b>Stato attuale:</b>\n{dati_attuali}"
                 
                if invia_messaggio_telegram(messaggio, URL):
                    notifica_inviata = True
                    
            else:
                
                print("Invio messaggio non necessario")

        # Se una notifica è stata inviata con successo, aggiorna i file
        if notifica_inviata:
            salva_dati_attuali(dati_attuali)
            salva_timestamp_notifica()
            print("Cache aggiornata")

    except Exception as e:
        print(f"Si è verificato un errore: {e}")
        invia_messaggio_telegram(f"☠️ Errore nello script alle {datetime.now().strftime('%H:%M')}:\n<pre>{e}</pre>", URL)

if __name__ == '__main__':
    controlla_biglietti()

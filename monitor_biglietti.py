import requests
import os
import json
from datetime import datetime
import time

# --- CONFIGURAZIONE ---
# Legge i dati esclusivamente dai "Secrets" (variabili d'ambiente)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('MONITOR_URL')

JSONBIN_API_KEY = os.environ.get('JSONBIN_API_KEY')
JSONBIN_ID = os.environ.get('JSONBIN_ID')
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

ORE_PER_NOTIFICA_ATTIVA = 8
# --- FINE CONFIGURAZIONE ---

def leggi_stato_online():
    """Legge lo stato precedente (dati biglietti e timestamp) da JSONBin.io."""
    print("--- Leggendo lo stato da JSONBin.io...")
    headers = {'X-Master-Key': JSONBIN_API_KEY}
    try:
        res = requests.get(f"{JSONBIN_URL}/latest", headers=headers, timeout=10)
        res.raise_for_status()
        dati = res.json()
        print("--- Stato letto con successo.")
        return dati.get('record', {})
    except Exception as e:
        print(f"Errore leggendo da JSONBin: {e}")
        return None

def salva_stato_online(nuovi_dati_biglietti, nuovo_timestamp):
    """Salva il nuovo stato su JSONBin.io."""
    print("--- Salvando il nuovo stato su JSONBin.io...")
    headers = {'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_API_KEY}
    payload = {"dati_biglietti": nuovi_dati_biglietti, "timestamp_notifica": nuovo_timestamp}
    try:
        res = requests.put(JSONBIN_URL, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        print("--- Nuovo stato salvato con successo.")
    except Exception as e:
        print(f"Errore salvando su JSONBin: {e}")

def invia_messaggio_telegram(messaggio, url_bottone):
    """Invia un messaggio con un bottone inline."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Token o Chat ID di Telegram non impostati.")
        return False
    
    tastiera = {'inline_keyboard': [[{'text': '➡️ VAI ALLA PAGINA ⬅️', 'url': url_bottone}]]}
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': messaggio, 'parse_mode': 'HTML', 'reply_markup': json.dumps(tastiera)}
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
    """Estrae i dettagli dei biglietti, li confronta e notifica le variazioni."""
    if not all([URL, JSONBIN_API_KEY, JSONBIN_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("Errore: una o più variabili d'ambiente non sono state impostate.")
        return

    print(f"Avvio controllo biglietti alle {datetime.now().strftime('%H:%M:%S')}...")
    
    stato_precedente = leggi_stato_online()
    if stato_precedente is None:
        print("Impossibile recuperare lo stato precedente. Riprovo più tardi.")
        return

    dati_precedenti = stato_precedente.get('dati_biglietti')
    timestamp_notifica_precedente = float(stato_precedente.get('timestamp_notifica', 0))

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
        
        orario_controllo = datetime.now().strftime("%H:%M del %d/%m/%Y")
        
        notifica_da_inviare = False
        messaggio = ""

        if dati_precedenti == "stato_iniziale" or dati_precedenti is None:
            messaggio = f"✅ <b>Monitoraggio avviato</b>\n<i>Controllo delle {orario_controllo}</i>\n\n<b>Biglietti trovati:</b>\n{dati_attuali}"
            notifica_da_inviare = True
        elif dati_attuali != dati_precedenti:
            messaggio = f"❗️<b>Variazione Rilevata!</b>❗️\n<i>Controllo delle {orario_controllo}</i>\n\n<b>Nuovi dati:</b>\n{dati_attuali}"
            notifica_da_inviare = True
        else:
            print("Nessuna variazione rilevata.")
            if (time.time() - timestamp_notifica_precedente) > (ORE_PER_NOTIFICA_ATTIVA * 3600):
                messaggio = f"✅ <b>Monitoraggio attivo</b>\n<i>Nessuna variazione da >{ORE_PER_NOTIFICA_ATTIVA} ore (controllo delle {orario_controllo})</i>\n\n<b>Stato attuale:</b>\n{dati_attuali}"
                notifica_da_inviare = True

        if notifica_da_inviare:
            if invia_messaggio_telegram(messaggio, URL):
                salva_stato_online(dati_attuali, time.time())

    except Exception as e:
        print(f"Si è verificato un errore critico: {e}")
        invia_messaggio_telegram(f"☠️ Errore nello script alle {datetime.now().strftime('%H:%M')}:\n<pre>{e}</pre>", URL)

if __name__ == '__main__':
    controlla_biglietti()

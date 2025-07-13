import requests
from bs4 import BeautifulSoup
import os

# --- CONFIGURAZIONE ---
# Le credenziali e l'URL verranno letti dalle "Secrets" di GitHub
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('MONITOR_URL')

# Il file ora salva una "fotografia" testuale dei dati, non solo un numero.

FILE_DATI = 'dati_biglietti.txt'
# --- FINE CONFIGURAZIONE ---

def leggi_dati_precedenti():
    """Legge i dati testuali dall'ultima esecuzione."""
    try:
        with open(FILE_DATI, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

def salva_dati_attuali(dati):
    """Salva i dati testuali correnti su file."""
    with open(FILE_DATI, 'w', encoding='utf-8') as f:
        f.write(dati)

# ▼▼▼ FUNZIONE MODIFICATA ▼▼▼
def invia_messaggio_telegram(messaggio, url_bottone):
    """Invia un messaggio con un bottone inline."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Token o Chat ID di Telegram non impostati.")
        return
    
    # Costruisce la tastiera con il bottone
    tastiera = {
        'inline_keyboard': [
            [
                {
                    'text': '➡️ VAI ALLA PAGINA ⬅️',
                    'url': url_bottone
                }
            ]
        ]
    }

    url_telegram = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': messaggio,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps(tastiera) # Converte la tastiera in formato JSON
    }
    try:
        response = requests.post(url_telegram, data=payload)
        response.raise_for_status()
        print("Messaggio inviato con successo a Telegram!")
    except requests.exceptions.RequestException as e:
        print(f"Errore durante l'invio del messaggio a Telegram: {e}")

def controlla_biglietti():
    """Estrae i dettagli dei biglietti e notifica le variazioni."""
    if not URL:
        print("Errore: URL di monitoraggio non impostato.")
        return
        
    print("Avvio controllo biglietti...")

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
            print(f"Trovati {len(elementi_biglietti)} biglietti.")
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
        
        if dati_precedenti is None:
            messaggio = f"✅ <b>Monitoraggio avviato</b>\n\n<b>Biglietti trovati:</b>\n{dati_attuali}"
            # ▼▼▼ CHIAMATA ALLA FUNZIONE MODIFICATA ▼▼▼
            invia_messaggio_telegram(messaggio, URL)
        elif dati_attuali != dati_precedenti:
            messaggio = f"❗️<b>Variazione Biglietti Rilevata!</b>❗️\n\n<b>Nuovi dati:</b>\n{dati_attuali}"
            # ▼▼▼ CHIAMATA ALLA FUNZIONE MODIFICATA ▼▼▼
            invia_messaggio_telegram(messaggio, URL)
        else:
            print("Nessuna variazione rilevata.")
        
        salva_dati_attuali(dati_attuali)

    except Exception as e:
        print(f"Si è verificato un errore: {e}")
        invia_messaggio_telegram(f"☠️ Errore nello script di monitoraggio:\n{e}", URL)

if __name__ == '__main__':
    controlla_biglietti()

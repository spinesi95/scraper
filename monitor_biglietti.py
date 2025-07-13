import requests
from bs4 import BeautifulSoup
import os

# --- CONFIGURAZIONE ---
# Le credenziali e l'URL verranno letti dalle "Secrets" di GitHub
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('MONITOR_URL') # URL letto dai secret

# File per salvare l'ultimo conteggio
FILE_CONTEGGIO = 'ultimo_conteggio.txt'
# --- FINE CONFIGURAZIONE ---

def leggi_ultimo_conteggio():
    """Legge l'ultimo conteggio da un file."""
    try:
        with open(FILE_CONTEGGIO, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def salva_conteggio(conteggio):
    """Salva il conteggio corrente su file."""
    with open(FILE_CONTEGGIO, 'w') as f:
        f.write(str(conteggio))

def invia_messaggio_telegram(messaggio):
    """Invia un messaggio a un utente o canale Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Token o Chat ID di Telegram non impostati.")
        return

    url_telegram = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': messaggio, 'parse_mode': 'HTML'}
    try:
        response = requests.post(url_telegram, data=payload)
        response.raise_for_status()
        print("Messaggio inviato con successo a Telegram!")
    except requests.exceptions.RequestException as e:
        print(f"Errore durante l'invio del messaggio a Telegram: {e}")

def controlla_biglietti():
    """Controlla il numero di biglietti disponibili e notifica se cambia."""
    if not URL:
        print("Errore: URL di monitoraggio non impostato.")
        return
        
    print("Avvio controllo biglietti...")
    ultimo_numero_biglietti = leggi_ultimo_conteggio()

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        elementi_biglietti = soup.find_all('div', class_='ticket-info showing')
        numero_biglietti_attuale = len(elementi_biglietti)

        print(f"Biglietti trovati: {numero_biglietti_attuale}. Ultimo conteggio: {ultimo_numero_biglietti}")

        if ultimo_numero_biglietti is None:
            messaggio = f"✅ Avviato il monitoraggio. Trovati {numero_biglietti_attuale} biglietti."
            invia_messaggio_telegram(messaggio)
        elif numero_biglietti_attuale != ultimo_numero_biglietti:
            messaggio = f"❗️<b>Variazione Biglietti!</b> Da {ultimo_numero_biglietti} a <b>{numero_biglietti_attuale}</b>.\nControlla: {URL}"
            invia_messaggio_telegram(messaggio)
        else:
            print("Nessuna variazione.")
        
        salva_conteggio(numero_biglietti_attuale)

    except Exception as e:
        print(f"Si è verificato un errore: {e}")

if __name__ == '__main__':
    controlla_biglietti()
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import date, timedelta
import time


# --- CONFIGURAZIONE ---
# Legge i dati esclusivamente dai "Secrets" (variabili d'ambiente)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')


BASE_URL_RM_MI = "https://trovaunposto.it/trains/searchTrainTicket?departure=ROMA%28TUTTE+LE+STAZIONI%29&arrival=MILANO%28TUTTE+LE+STAZIONI%29&date="
BASE_URL_MI_RM = "https://trovaunposto.it/trains/searchTrainTicket?departure=MILANO%28TUTTE+LE+STAZIONI%29&arrival=ROMA%28TUTTE+LE+STAZIONI%29&date="
MESI_DA_CONTROLLARE = 4
# --- FINE CONFIGURAZIONE ---


def invia_messaggio_telegram(testo):
    """Invia un messaggio a Telegram, dividendolo se supera i 4096 caratteri."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Token o Chat ID di Telegram non impostati.")
        return

    url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    max_len = 4096
    
    # Suddivide il testo in più messaggi se necessario
    messaggi = [testo[i:i + max_len] for i in range(0, len(testo), max_len)]

    for messaggio_chunk in messaggi:
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': messaggio_chunk,
            'parse_mode': 'HTML'
        }
        try:
            response = requests.post(url_api, data=payload)
            response.raise_for_status()
            print("Messaggio inviato con successo.")
            time.sleep(1) # Pausa tra un messaggio e l'altro
        except requests.exceptions.RequestException as e:
            print(f"Errore durante l'invio del messaggio: {e}")


def estrai_biglietti(url):
    """Estrae i dettagli dei biglietti da un dato URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        elementi = soup.find_all('div', class_='ticket-info showing')
        if not elementi:
            return ["  <i>Nessun biglietto trovato</i>"]

        lista_dettagli = []
        for ticket in elementi:
            orario_el = ticket.find('div', class_='col-20 block time')
            tratta_el = ticket.find('div', class_='col-30 block mobile-pl tra_stat_title')
            prezzo_el = ticket.find('div', class_='col-16 block mob-right')
            
            orario = " ".join(orario_el.text.strip().split()) if orario_el else "N/D"
            tratta = " ".join(tratta_el.text.strip().split()) if tratta_el else "N/D"
            prezzo = " ".join(prezzo_el.text.strip().split()) if prezzo_el else "N/D"
            
            lista_dettagli.append(f"  • {orario} | {tratta} | <b>{prezzo}</b>")
        return lista_dettagli

    except Exception as e:
        print(f"Errore durante lo scraping di {url}: {e}")
        return [f"  <i>Errore durante il caricamento: {e}</i>"]


def genera_report_per_giorno(giorno_settimana, titolo, base_url):
    """Genera una sezione del report per un dato giorno della settimana."""
    oggi = date.today()
    data_fine = oggi + timedelta(days=MESI_DA_CONTROLLARE * 30)
    giorni_da_controllare = []
    
    giorno_corrente = oggi
    while giorno_corrente <= data_fine:
        if giorno_corrente.weekday() == giorno_settimana: # 4 = Venerdì, 6 = Domenica
            giorni_da_controllare.append(giorno_corrente)
        giorno_corrente += timedelta(days=1)
        
    report_completo = f"<b>{titolo}</b>\n\n"
    
    for giorno in giorni_da_controllare:
        data_formattata_url = giorno.strftime("%Y-%m-%d")
        data_formattata_msg = giorno.strftime("%d/%m/%Y")
        url_completo = base_url + data_formattata_url
        
        print(f"Controllo {titolo} per il {data_formattata_msg}...")
        report_completo += f"🗓️ <u>{data_formattata_msg}</u>\n"
        
        biglietti = estrai_biglietti(url_completo)
        report_completo += "\n".join(biglietti)
        report_completo += "\n\n"
        
        time.sleep(1.5) # Pausa per non sovraccaricare il server

    return report_completo


if __name__ == '__main__':
    print("--- Avvio Report Prezzi Treni ---")
    
    report_venerdi = genera_report_per_giorno(4, "🚆 ROMA ➡️ MILANO (Venerdì)", BASE_URL_RM_MI)
    report_domenica = genera_report_per_giorno(6, "🚆 MILANO ➡️ ROMA (Domenica)", BASE_URL_MI_RM)
    
    messaggio_finale = report_venerdi + "------------------------------\n\n" + report_domenica
    
    print("--- Invio del report a Telegram ---")
    invia_messaggio_telegram(messaggio_finale)
    print("--- Report Inviato ---")

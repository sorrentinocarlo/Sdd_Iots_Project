import sys
import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Definizione degli ambiti di accesso per i servizi Google
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = '/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/credentials.json'

def authenticate_google_services():
    """
    Autentica l'utente con i servizi di Google Drive e Google Sheets.

    Controlla se le credenziali salvate esistono, altrimenti avvia il flusso di autenticazione.
    Restituisce i servizi autenticati di Google Drive e Google Sheets.

    Returns:
        drive_service: Il servizio autenticato di Google Drive.
        sheets_service: Il servizio autenticato di Google Sheets.
    """
    creds = None
    # Controlla se il token di autenticazione esiste
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # Se le credenziali non sono valide o mancano, avvia il flusso di autenticazione
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Salva le credenziali per il prossimo accesso
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # Costruisce i servizi Google autenticati
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return drive_service, sheets_service

def find_or_create_folder(drive_service, folder_name):
    """
    Trova o crea una cartella su Google Drive con il nome specificato.

    Args:
        drive_service: Il servizio autenticato di Google Drive.
        folder_name: Il nome della cartella da cercare o creare.

    Returns:
        folder_id: L'ID della cartella trovata o creata.
    """
    # Query per trovare la cartella con il nome specificato
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = response.get('files', [])
    
    # Se la cartella non esiste, creala
    if not folders:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    else:
        return folders[0].get('id')

def find_or_create_sheet(drive_service, sheets_service, folder_id, sheet_name):
    """
    Trova o crea un foglio di calcolo su Google Sheets con il nome specificato all'interno di una cartella.

    Args:
        drive_service: Il servizio autenticato di Google Drive.
        sheets_service: Il servizio autenticato di Google Sheets.
        folder_id: L'ID della cartella in cui cercare o creare il foglio.
        sheet_name: Il nome del foglio da cercare o creare.

    Returns:
        sheet_id: L'ID del foglio trovato o creato.
    """
    # Query per trovare il foglio con il nome specificato all'interno della cartella
    query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    
    # Se il foglio non esiste, crealo
    if not files:
        file_metadata = {
            'name': sheet_name,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [folder_id]
        }
        sheet = drive_service.files().create(body=file_metadata, fields='id').execute()
        sheet_id = sheet.get('id')
        setup_sheet(sheets_service, sheet_id)
        return sheet_id
    else:
        return files[0]['id']

def setup_sheet(sheets_service, sheet_id):
    """
    Imposta le intestazioni per un nuovo foglio di calcolo.

    Args:
        sheets_service: Il servizio autenticato di Google Sheets.
        sheet_id: L'ID del foglio su cui impostare le intestazioni.

    Returns:
        None
    """
    headers = [["Operazione", "Chiave", "IV"]]
    body = {'values': headers}
    range_name = 'A1:C1'
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption='RAW', body=body).execute()

def append_data_to_sheet(sheets_service, sheet_id, data):
    """
    Aggiunge una riga di dati a un foglio di calcolo su Google Sheets.

    Args:
        sheets_service: Il servizio autenticato di Google Sheets.
        sheet_id: L'ID del foglio a cui aggiungere i dati.
        data: La lista di dati da aggiungere al foglio.

    Returns:
        None
    """
    body = {'values': [data]}
    range_name = 'A:C'
    sheets_service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS', body=body).execute()

def check_existing_key(sheets_service, sheet_id, operation_name):
    """
    Verifica se una chiave esiste già in un foglio di calcolo specificato.

    Args:
        sheets_service: Il servizio autenticato di Google Sheets.
        sheet_id: L'ID del foglio in cui cercare la chiave.
        operation_name: Il nome dell'operazione per cui cercare la chiave.

    Returns:
        Tuple contenente (key, IV) se la chiave esiste, altrimenti (None, None).
    """
    try:
        range = 'A:C'
        result = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range).execute()
        values = result.get('values', [])
        for row in values:
            if row[0] == operation_name:
                return row[1], row[2]  # Restituisce la chiave e l'IV se trovati
    except Exception as e:
        print(f"Errore durante la verifica della chiave esistente: {e}")
    return None, None  # Restituisce None se non trovato

if __name__ == "__main__":
    # Verifica gli argomenti della riga di comando
    if len(sys.argv) != 6:
        print("Uso: python keyChainGsheet.py <tipo_foglio> <nome_file> <cartella_destinazione> <chiave> <iv>")
        sys.exit(1)

    tipo_foglio, nome_file, cartella_destinazione, chiave, iv = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
    drive_service, sheets_service = authenticate_google_services()
    folder_id = find_or_create_folder(drive_service, cartella_destinazione)
    sheet_id = find_or_create_sheet(drive_service, sheets_service, folder_id, "ChiaviCorso")

    existing_key, existing_iv = check_existing_key(sheets_service, sheet_id, nome_file)
    if existing_key and existing_iv:
        print(existing_key, existing_iv)  # Stampa la chiave e l'IV esistenti se trovati
    else:
        data = [nome_file, chiave, iv]  # Include IV nei dati
        append_data_to_sheet(sheets_service, sheet_id, data)
        print(1)  # Indica che nessuna chiave esistente è stata trovata e sono stati aggiunti nuovi dati

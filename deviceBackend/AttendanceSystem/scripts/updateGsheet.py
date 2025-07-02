import sys
import os
import pickle
from googleapiclient.discovery import build
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
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Salva le credenziali per il prossimo accesso
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # Costruisce e restituisce i servizi autenticati
    return build('drive', 'v3', credentials=creds), build('sheets', 'v4', credentials=creds)

def find_in_subfolders(drive_service, folder_id, sheet_name):
    """
    Cerca ricorsivamente un foglio di calcolo in tutte le sottocartelle di una cartella specificata.

    Args:
        drive_service: Il servizio autenticato di Google Drive.
        folder_id: L'ID della cartella in cui cercare ricorsivamente.
        sheet_name: Il nome del foglio di calcolo da cercare.

    Returns:
        found_id: L'ID del foglio di calcolo trovato o None se non trovato.
    """
    # Query per trovare tutte le sottocartelle all'interno della cartella specificata
    query_subfolders = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    response_subfolders = drive_service.files().list(q=query_subfolders, spaces='drive', fields='files(id, name, mimeType)').execute()
    folders = response_subfolders.get('files', [])
    
    for folder in folders:
        # Ricorsione: cerca il foglio nella sottocartella corrente
        found_id = find_sheet_id_by_name(drive_service, folder['name'], sheet_name, folder['id'])
        if found_id:
            return found_id
    return None

def find_sheet_id_by_name(drive_service, folder_name, sheet_name, parent_folder_id=None):
    """
    Trova l'ID di un foglio di calcolo Google Sheets in una cartella specificata, cercando ricorsivamente nelle sottocartelle.

    Args:
        drive_service: Il servizio autenticato di Google Drive.
        folder_name: Il nome della cartella principale.
        sheet_name: Il nome del foglio di calcolo da cercare.
        parent_folder_id: (Opzionale) L'ID della cartella principale in cui cercare.

    Returns:
        sheet_id: L'ID del foglio di calcolo trovato o None se non trovato.
    """
    if parent_folder_id is None:
        # Se l'ID della cartella principale non è specificato, trova l'ID della cartella con il nome dato
        query_folder = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
        response_folder = drive_service.files().list(q=query_folder, spaces='drive', fields='files(id, name)').execute()
        folders = response_folder.get('files', [])
        if not folders:
            print(f"Cartella {folder_name} non trovata.")
            return None
        folder_id = folders[0].get('id')
    else:
        folder_id = parent_folder_id

    # Cerca il foglio di calcolo con il nome specificato all'interno della cartella trovata
    query_file = f"mimeType='application/vnd.google-apps.spreadsheet' and name='{sheet_name}' and '{folder_id}' in parents"
    response_file = drive_service.files().list(q=query_file, spaces='drive', fields='files(id, name)').execute()
    files = response_file.get('files', [])
    
    if not files:
        # Se il foglio non è trovato, cerca ricorsivamente nelle sottocartelle
        return find_in_subfolders(drive_service, folder_id, sheet_name)
    else:
        return files[0].get('id')

def append_data_to_sheet(sheets_service, sheet_id, data, range_name):
    """
    Aggiunge una riga di dati a un foglio di calcolo su Google Sheets.

    Args:
        sheets_service: Il servizio autenticato di Google Sheets.
        sheet_id: L'ID del foglio di calcolo a cui aggiungere i dati.
        data: La lista di dati da aggiungere al foglio di calcolo.
        range_name: Il range nel foglio di calcolo dove aggiungere i dati.

    Returns:
        None
    """
    value_input_option = 'USER_ENTERED'
    insert_data_option = 'INSERT_ROWS'
    value_range_body = {"values": [data]}

    # Richiesta per aggiungere i dati al foglio di calcolo
    request = sheets_service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption=value_input_option, insertDataOption=insert_data_option,
        body=value_range_body)
    response = request.execute()
    print(f"Dati aggiunti con successo al foglio. ID riga: {response.get('updates').get('updatedRange')}")

if __name__ == "__main__":
    # Controlla il numero di argomenti passati dalla riga di comando
    argc = len(sys.argv)
    if argc not in [7, 8]:
        print("Uso: python updateGsheet.py <nome_file> <cartella_destinazione> <id> <nome> <cognome> <matricola> [orario_arrivo]")
        sys.exit(1)
    else:
        file_name, folder_name, student_id, first_name, last_name, matriculation_number = sys.argv[1:7]
        orario_arrivo = sys.argv[7] if argc == 8 else None
        range_name = 'A:F' if orario_arrivo else 'A:E'

        # Autentica i servizi Google e trova l'ID del foglio di calcolo
        drive_service, sheets_service = authenticate_google_services()
        sheet_id = find_sheet_id_by_name(drive_service, folder_name, file_name)
        if sheet_id:
            # Prepara i dati da aggiungere al foglio di calcolo
            data = [student_id, first_name, last_name, matriculation_number]
            if orario_arrivo:
                data.append(orario_arrivo)
            # Aggiunge i dati al foglio di calcolo
            append_data_to_sheet(sheets_service, sheet_id, data, range_name)
        else:
            print("Foglio non trovato.")

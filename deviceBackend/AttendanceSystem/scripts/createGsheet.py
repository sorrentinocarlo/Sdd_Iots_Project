import sys
import os
import pickle
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
            creds = flow.run_local_server(port=3000)
        # Salva le credenziali per il prossimo accesso
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # Costruisce i servizi Google autenticati
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return drive_service, sheets_service

def find_or_create_folder(drive_service, folder_name, parent_id=None):
    """
    Trova o crea una cartella su Google Drive con il nome specificato.

    Args:
        drive_service: Il servizio autenticato di Google Drive.
        folder_name: Il nome della cartella da cercare o creare.
        parent_id: (Opzionale) L'ID della cartella principale in cui cercare o creare la nuova cartella.

    Returns:
        folder_id: L'ID della cartella trovata o creata.
    """
    # Query per trovare la cartella con il nome specificato
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    response = drive_service.files().list(q=query, spaces='drive').execute()
    folders = response.get('files', [])
    
    # Se la cartella non esiste, la crea
    if not folders:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id:
            file_metadata['parents'] = [parent_id]
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    else:
        return folders[0].get('id')

def find_file_by_name(drive_service, file_name, folder_id):
    """
    Trova un file su Google Drive con il nome specificato all'interno di una cartella specificata.

    Args:
        drive_service: Il servizio autenticato di Google Drive.
        file_name: Il nome del file da cercare.
        folder_id: L'ID della cartella in cui cercare il file.

    Returns:
        file_id: L'ID del file trovato o None se non esiste.
    """
    # Query per trovare il file con il nome specificato e all'interno della cartella specificata
    query = f"mimeType='application/vnd.google-apps.spreadsheet' and name='{file_name}' and '{folder_id}' in parents"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    return files[0].get('id') if files else None

def create_sheet(drive_service, sheets_service, sheet_type, file_name, folder_name):
    """
    Crea un nuovo foglio di calcolo su Google Sheets in una cartella specificata.

    Args:
        drive_service: Il servizio autenticato di Google Drive.
        sheets_service: Il servizio autenticato di Google Sheets.
        sheet_type: Il tipo di foglio ('R' per Registrazione, 'L' per Lezione, 'E' per Esame).
        file_name: Il nome del nuovo foglio di calcolo.
        folder_name: Il nome della cartella in cui creare il foglio.

    Returns:
        None
    """
    # Trova o crea la cartella principale in cui salvare il foglio
    main_folder_id = find_or_create_folder(drive_service, folder_name)
    
    # Se il tipo di foglio è 'E', crea o trova una sottocartella chiamata 'Esami'
    if sheet_type == "E":
        exam_folder_name = "Esami"
        folder_id = find_or_create_folder(drive_service, exam_folder_name, main_folder_id)
    else:
        folder_id = main_folder_id

    # Controlla se esiste già un file con lo stesso nome
    existing_file_id = find_file_by_name(drive_service, file_name, folder_id)
    if existing_file_id:
        print(f"Esiste già un foglio con nome '{file_name}'. ID: {existing_file_id}")
        return

    # Se il file non esiste, crea il foglio di calcolo
    spreadsheet_body = {'properties': {'title': file_name}, 'sheets': [{'properties': {'title': sheet_type}}]}
    spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet_body).execute()
    sheet_id = spreadsheet['spreadsheetId']
    
    # Imposta le intestazioni per il foglio in base al tipo
    headers_map = {
        "R": [["Tag_ID", "Nome", "Cognome", "Matricola"]],
        "L": [["Tag_ID", "Nome", "Cognome", "Matricola", "Orario di arrivo"]],
        "E": [["Tag_ID", "Nome", "Cognome", "Matricola", "Voto"]]
    }
    headers = headers_map.get(sheet_type, [])
    if headers:
        resource = {"values": headers}
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"{sheet_type}!A1", body=resource, valueInputOption="RAW").execute()

    # Sposta il nuovo foglio nella cartella specificata
    drive_service.files().update(fileId=sheet_id, addParents=folder_id, removeParents='root', fields='id, parents').execute()

    print(f"Foglio creato con successo. ID: {sheet_id}")
    print(f"URL: {spreadsheet['spreadsheetUrl']}")

if __name__ == "__main__":
    # Verifica gli argomenti della riga di comando
    if len(sys.argv) != 4:
        print("Uso: python createGsheet.py <tipo_foglio> <nome_file> <nome_cartella_destinazione>")
    else:
        sheet_type, file_name, folder_name = sys.argv[1], sys.argv[2], sys.argv[3]
        drive_service, sheets_service = authenticate_google_services()
        create_sheet(drive_service, sheets_service, sheet_type, file_name, folder_name)

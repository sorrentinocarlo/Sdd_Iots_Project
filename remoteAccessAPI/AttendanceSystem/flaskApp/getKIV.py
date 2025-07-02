import sys
import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'credentials.json'

def authenticate_google_services():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return drive_service, sheets_service

def find_or_create_folder(drive_service, folder_name):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = response.get('files', [])
    if not folders:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    else:
        return folders[0].get('id')

def find_or_create_sheet(drive_service, sheets_service, folder_id, sheet_name):
    query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
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
    headers = [["Operazione", "Chiave", "IV"]]
    body = {'values': headers}
    range_name = 'A1:C1'
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption='RAW', body=body).execute()

def append_data_to_sheet(sheets_service, sheet_id, data):
    body = {'values': [data]}
    range_name = 'A:C'
    sheets_service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS', body=body).execute()

def check_existing_key(sheets_service, sheet_id, operation_name):
    try:
        # print(f"Checking existing key for operation: {operation_name}")
        range = 'A:C'
        result = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range).execute()
        values = result.get('values', [])
        # print(f"Values found in sheet: {values}")
        for row in values:
            if row[0] == operation_name:
                # print(f"Match found: {row}")
                return row[1], row[2]  # Return the key and IV if found
    except Exception as e:
        print(f"Error checking existing key: {e}")
    return None, None  # Return None if not found


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python getKeyIV.py <operation_type> <course_name> <additional_info>")
        sys.exit(1)

    operazione, corso, infoAgg = sys.argv[1], sys.argv[2], sys.argv[3]
    drive_service, sheets_service = authenticate_google_services()
    folder_id = find_or_create_folder(drive_service, corso)
    sheet_id = find_or_create_sheet(drive_service, sheets_service, folder_id, "ChiaviCorso")

    if operazione == "Registrazione":
        existing_key, existing_iv = check_existing_key(sheets_service, sheet_id, operazione)
        if existing_key and existing_iv:
            print(existing_key, existing_iv)  # Print the existing key and IV if found
        else:
            print(1)  # Indicate that no existing key was found
    elif operazione == "Lezione" or operazione == "Esame":
        existing_key, existing_iv = check_existing_key(sheets_service, sheet_id, infoAgg)
        if existing_key and existing_iv:
            print(existing_key, existing_iv)  # Print the existing key and IV if found
        else:
            print(1)  # Indicate that no existing key was found
    else:
        print(1)  # Indicate that no existing key was found
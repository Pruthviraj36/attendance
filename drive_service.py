from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import os
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'service_account.json'

def authenticate_drive():
    creds = None
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def get_or_create_folder(service, folder_name, parent_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def upload_file_to_drive(file_path, root_folder_id=None):
    creds = authenticate_drive()
    if not creds:
        print("No credentials found.")
        return None

    service = build('drive', 'v3', credentials=creds)
    
    # Logic: Root -> Attendance -> {Date}
    # If root_folder_id is provided, use it as the base "Attendance" folder or parent of it.
    # For this implementation, let's assume root_folder_id IS the "Attendance" folder if provided,
    # or we create "Attendance" in the root.
    
    attendance_folder_id = root_folder_id
    if not attendance_folder_id:
        attendance_folder_id = get_or_create_folder(service, 'Attendance')
        
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_folder_id = get_or_create_folder(service, date_str, parent_id=attendance_folder_id)
    
    file_name = os.path.basename(file_path)
    file_metadata = {
        'name': file_name,
        'parents': [date_folder_id]
    }
        
    media = MediaFileUpload(file_path, mimetype='text/csv')
    
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

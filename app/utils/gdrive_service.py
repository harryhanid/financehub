import os
import io
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from werkzeug.datastructures import FileStorage
import config

# Scope yang dibutuhkan untuk memanipulasi file Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_gdrive_service():
    """
    Membangun dan mengembalikan objek service Google Drive API menggunakan OAuth 2.0.
    """
    creds = None
    token_path = os.path.join(config.BASE_DIR, 'token.json')
    client_secret_path = os.path.join(config.BASE_DIR, 'client_secret.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(f"File {client_secret_path} tidak ditemukan.")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    service = build('drive', 'v3', credentials=creds)
    return service

def create_gdrive_folder(folder_name: str) -> str:
    """
    Membuat folder baru di dalam GDRIVE_FOLDER_ID dan mengembalikan ID folder tersebut.
    Jika folder dengan nama yang sama sudah ada, akan mengembalikan ID folder yang sudah ada.
    """
    service = get_gdrive_service()
    if not config.GDRIVE_FOLDER_ID:
        raise ValueError("GDRIVE_FOLDER_ID belum diatur di .env atau config.py")

    # Cari apakah folder sudah ada
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{config.GDRIVE_FOLDER_ID}' in parents and trashed=false"
    results = service.files().list(
        q=query, 
        spaces='drive', 
        fields='files(id, name)', 
        supportsAllDrives=True, 
        includeItemsFromAllDrives=True
    ).execute()
    
    items = results.get('files', [])
    if items:
        # Jika sudah ada, kembalikan ID folder pertama yang ditemukan
        return items[0]['id']

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [config.GDRIVE_FOLDER_ID]
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    
    return folder.get('id')

def delete_gdrive_file(file_id: str):
    """
    Menghapus file secara permanen dari Google Drive berdasarkan ID.
    """
    service = get_gdrive_service()
    try:
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
    except Exception as e:
        print(f"Gagal menghapus file {file_id}: {e}")

def upload_file_to_gdrive(file_obj: FileStorage, filename: str, mime_type: str, parent_folder_id: str = None) -> str:
    """
    Mengunggah file (dari request flask) ke Google Drive.
    Mengembalikan 'file_id' dari Google Drive jika sukses.
    """
    service = get_gdrive_service()
    
    parent_id = parent_folder_id or config.GDRIVE_FOLDER_ID
    if not parent_id:
        raise ValueError("GDRIVE_FOLDER_ID belum diatur di .env atau config.py")

    file_metadata = {
        'name': filename,
        'parents': [parent_id]
    }
    
    # Baca data file sebagai byte stream agar tidak memakan RAM berlebih untuk file besar
    file_stream = io.BytesIO(file_obj.read())
    
    media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)
    
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name',
        supportsAllDrives=True
    ).execute()
    
    # Kembalikan cursor stream file ke awal jika file butuh dibaca lagi
    file_obj.seek(0)
    
    return uploaded_file.get('id')

def get_file_stream_from_gdrive(file_id: str) -> io.BytesIO:
    """
    Mengunduh file dari Google Drive dalam bentuk byte stream.
    Sangat berguna untuk fitur 'Backend Proxy' di mana Flask meneruskan file ke Frontend.
    """
    service = get_gdrive_service()
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    
    while done is False:
        status, done = downloader.next_chunk()
        
    file_stream.seek(0)
    return file_stream

def get_file_metadata_from_gdrive(file_id: str) -> dict:
    """
    Mengambil metadata file (nama, mimeType) dari Google Drive.
    """
    service = get_gdrive_service()
    return service.files().get(fileId=file_id, fields="name, mimeType", supportsAllDrives=True).execute()

import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

GDRIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gdrive')

_drive_instance = None

def get_drive():
    global _drive_instance
    if _drive_instance is None:
        gauth = GoogleAuth(settings_file=os.path.join(GDRIVE_DIR, 'settings.yaml'))
        gauth.LocalWebserverAuth()
        _drive_instance = GoogleDrive(gauth)
    return _drive_instance

def upload_file(filename, content):
    drive = get_drive()
    try:
        file_list = drive.ListFile({'q': f"title='{filename}' and trashed=false"}).GetList()
        if file_list:
            file = drive.CreateFile({'id': file_list[0]['id']})
            file.SetContentFile(content)
            file.Upload()
        else:
            file = drive.CreateFile({'title': filename})
            file.SetContentFile(content)
            file.Upload()
    except Exception as e:
        print(f"Error uploading file '{filename}': {e}")

def get_file(filename, path=None):
    drive = get_drive()
    if path is None:
        path = filename
    try:
        file_list = drive.ListFile({'q': f"title='{filename}' and trashed=false"}).GetList()
        if not file_list:
            raise FileNotFoundError(f"File '{filename}' not found in Google Drive.")
        file = drive.CreateFile({'id': file_list[0]['id']})
        file.GetContentFile(path)
    except Exception as e:
        print(f"Error downloading file '{filename}': {e}")


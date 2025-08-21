from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Path to your service account key
SERVICE_ACCOUNT_FILE = 'trade-468906-acd76b2d6718.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = "1RdOA6cIaeBHhnUjHSrj18rseDXDXO8Zs"

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

results = drive_service.files().list(q=f"'{FOLDER_ID}' in parents", fields="files(name)", includeItemsFromAllDrives=True,
    supportsAllDrives=True
).execute()
print(results)


def upload_file(file_path, file_name):
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True

    ).execute()
    print(f"Uploaded file ID: {file.get('id')}")
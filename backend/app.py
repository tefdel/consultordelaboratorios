import os
import io
from flask import Flask, jsonify, send_file
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = Flask(__name__)

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = '1tD5yicS3L3uUfl_j9asWk3PsWF4h5I4o'  # From the provided URL

def get_drive_service():
    """Create and return a Google Drive service object."""
    # Try to get credentials from environment variable or default file
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        # Look for service-account.json in current directory
        creds_path = 'service-account.json'
        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                f"Service account credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                f"environment variable or place service-account.json in {os.getcwd()}"
            )
    
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

@app.route('/')
def index():
    return jsonify({
        'message': 'Google Drive Backend API',
        'endpoints': {
            '/files': 'List files in the specified folder',
            '/files/<file_id>': 'Download a specific file by ID'
        }
    })

@app.route('/files')
def list_files():
    """List all files in the specified Google Drive folder."""
    try:
        service = get_drive_service()
        # Query for files in the specified folder
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            pageSize=100
        ).execute()
        
        items = results.get('files', [])
        
        # Format the response
        files = []
        for item in items:
            files.append({
                'id': item['id'],
                'name': item['name'],
                'mimeType': item['mimeType'],
                'size': item.get('size', '0'),
                'modifiedTime': item['modifiedTime']
            })
        
        return jsonify({
            'folder_id': FOLDER_ID,
            'count': len(files),
            'files': files
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files/<file_id>')
def download_file(file_id):
    """Download a specific file by its ID."""
    try:
        service = get_drive_service()
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id).execute()
        
        # Download the file
        request = service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while done is False:
            status, downloader = downloader.next_chunk()
            if status:
                done = status.progress() >= 1.0
        
        file_io.seek(0)
        
        # Return the file as a downloadable response
        return send_file(
            file_io,
            download_name=file_metadata['name'],
            mimetype=file_metadata['mimeType'],
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
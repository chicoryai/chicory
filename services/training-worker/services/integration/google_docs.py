from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import os
import time
from functools import wraps
from typing import Optional, List, Dict, Any

from services.utils.logger import logger

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Constants for retry mechanism
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_PAGE_SIZE = 1000

# Text-based MIME types to include
TEXT_MIME_TYPES = [
    'text/plain',
    'text/csv',
    'text/html',
    'text/javascript',
    'text/css',
    'application/json',
    'application/xml',
    'application/x-yaml',
    'application/markdown',
    'application/x-python-code',
    'application/vnd.google-apps.document',  # Google Docs
    'application/vnd.google-apps.spreadsheet',  # Google Sheets
    'image/png', # PNG files
    'image/jpeg', # JPG files
    'image/svg+xml',
    'image/webp',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-powerpoint', # PPT files
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # DOCX files
    'application/pdf', # PDF files
]

# List of MIME types to exclude (binary files, media, etc.)
EXCLUDED_BINARY_MIME_TYPES = [
    'video/mp4',  # MP4 files
    'video/quicktime',  # MOV files
    'application/x-apple-diskimage',  # DMG files
    'application/octet-stream',  # Generic binary files
    'application/zip',  # ZIP files
]

def retry_on_error(max_retries=MAX_RETRIES, initial_delay=INITIAL_RETRY_DELAY):
    """Decorator for retrying operations on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for retry in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except HttpError as e:
                    if e.resp.status in [429, 500, 503]:  # Rate limit or server errors
                        last_exception = e
                        logger.warning(f"Attempt {retry + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        raise  # Re-raise if it's a different HTTP error
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {retry + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2
            
            raise last_exception
        return wrapper
    return decorator

def authenticate_service_account(google_project_id, google_sa_pvt_key_id, google_sa_pvt_key, google_sa_client_email,
                                 google_sa_client_id, google_sa_client_cert_url):
    """Authenticate using a service account."""
    service_account_info = {
        "type": "service_account",
        "project_id": google_project_id,
        "private_key_id": google_sa_pvt_key_id,
        "private_key": google_sa_pvt_key,
        "client_email": google_sa_client_email,
        "client_id": google_sa_client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": google_sa_client_cert_url,
        "universe_domain": "googleapis.com"
    }

    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

@retry_on_error()
def get_folder_details(service, folder_id: Optional[str] = None, folder_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get folder details by ID or name.
    
    Args:
        service: Google Drive service instance
        folder_id: Optional folder ID
        folder_name: Optional folder name
    
    Returns:
        List of folder details
    
    Raises:
        HttpError: If the request fails due to permissions or invalid ID
        ValueError: If neither folder_id nor folder_name is provided
    """
    if not folder_id and not folder_name:
        raise ValueError("Either folder_id or folder_name must be provided")

    try:
        query = []
        if folder_id:
            query.append(f"id = '{folder_id}'")
        if folder_name:
            query.append(f"name = '{folder_name}'")
        query.append("mimeType = 'application/vnd.google-apps.folder'")
        
        results = service.files().list(
            q=" and ".join(query),
            fields="files(id, name, owners, permissions, trashed)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        # Filter out trashed folders
        return [f for f in folders if not f.get('trashed', False)]
    except HttpError as error:
        if error.resp.status == 404:
            logger.error(f"Folder not found: {folder_id or folder_name}")
            return []
        elif error.resp.status == 403:
            logger.error(f"Permission denied for folder: {folder_id or folder_name}")
            return []
        raise

@retry_on_error()
def list_files_recursive(service, folder_id: str, include_folders: bool = True) -> List[Dict[str, Any]]:
    """
    Recursively list all text files and subfolders in a folder.
    
    Args:
        service: Google Drive service instance
        folder_id: ID of the folder to list
        include_folders: Whether to include folders in the results
    
    Returns:
        List of file and folder details, filtered to only include text files
    
    Raises:
        HttpError: If the request fails due to permissions or invalid ID
    """
    all_items = []
    page_token = None
    
    try:
        while True:
            query = [f"'{folder_id}' in parents", "trashed = false"]  # Exclude trashed items

            # Add MIME type filter to exclude binary files
            exclude_conditions = [f"mimeType != '{mime_type}'" for mime_type in EXCLUDED_BINARY_MIME_TYPES]
            query.append(" and ".join(exclude_conditions))
            
            results = service.files().list(
                q=" and ".join(query),
                fields="nextPageToken, files(id, name, mimeType, owners, modifiedTime, size, md5Checksum)",
                pageToken=page_token,
                pageSize=MAX_PAGE_SIZE,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                orderBy="folder,name"  # Sort folders first, then by name
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                all_items.append(item)
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    try:
                        # Recursively get files from subfolder
                        sub_items = list_files_recursive(service, item['id'], include_folders)
                        all_items.extend(sub_items)
                    except HttpError as e:
                        if e.resp.status == 403:
                            logger.warning(f"Skipping subfolder {item['name']} due to permission denied")
                            continue
                        raise
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
        return all_items
    except HttpError as error:
        if error.resp.status == 404:
            logger.error(f"Folder not found: {folder_id}")
            return []
        elif error.resp.status == 403:
            logger.error(f"Permission denied for folder: {folder_id}")
            return []
        raise


@retry_on_error()
def list_all_files(service):
    """List all files accessible by the service account."""
    try:
        results = service.files().list(
            fields="files(id, name, owners, mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])
        return files
    except HttpError as error:
        logger.error(f"An error occurred: {error}", exc_info=True)
        return []


@retry_on_error()
def list_all_accessible_items(service, include_folders: bool = True) -> List[Dict[str, Any]]:
    """
    List all files and folders accessible by the service account.

    Args:
        service: Google Drive service instance
        include_folders: Whether to include folders in the results

    Returns:
        List of file and folder details

    Raises:
        HttpError: If the request fails
    """
    all_items = []
    page_token = None

    try:
        while True:
            # Base query for all accessible items
            query = ["trashed = false"]

            if not include_folders:
                # Exclude folders if include_folders is False
                query.append("mimeType != 'application/vnd.google-apps.folder'")

            # Exclude specific binary MIME types if necessary
            exclude_conditions = [f"mimeType != '{mime_type}'" for mime_type in EXCLUDED_BINARY_MIME_TYPES]
            query.append(" and ".join(exclude_conditions))

            results = service.files().list(
                q=" and ".join(query),
                fields="nextPageToken, files(id, name, mimeType, owners, modifiedTime, size, md5Checksum)",
                pageToken=page_token,
                pageSize=MAX_PAGE_SIZE,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                orderBy="folder,name"
            ).execute()

            items = results.get('files', [])
            all_items.extend(items)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        return all_items
    except HttpError as error:
        logger.error(f"An error occurred: {error}", exc_info=True)
        return []


@retry_on_error()
def download_file(service, file_id: str, file_name: str, save_path: str) -> bool:
    """
    Download a file from Google Drive.
    
    Args:
        service: Google Drive service instance
        file_id: ID of the file to download
        file_name: Name to save the file as
        save_path: Directory to save the file in
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    request = service.files().get_media(fileId=file_id)
    file_path = os.path.join(save_path, file_name)
    
    try:
        # Ensure save directory exists
        os.makedirs(save_path, exist_ok=True)
        
        # Check if file already exists
        if os.path.exists(file_path):
            logger.warning(f"File already exists: {file_path}")
            return False
            
        with open(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                try:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"Download {int(status.progress() * 100)}%.")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:  # Server errors
                        logger.warning("Temporary error, retrying chunk download...")
                        time.sleep(1)
                        continue
                    raise
                    
        logger.info(f"Downloaded: {file_name}")
        return True
        
    except HttpError as error:
        if error.resp.status == 404:
            logger.error(f"File not found: {file_id}")
        elif error.resp.status == 403:
            logger.error(f"Permission denied for file: {file_id}")
        else:
            logger.error(f"Error downloading {file_name}: {str(error)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return False
    except Exception as e:
        logger.error(f"An error occurred while downloading {file_name}: {str(e)}", exc_info=True)
        if os.path.exists(file_path):
            os.remove(file_path)
        return False

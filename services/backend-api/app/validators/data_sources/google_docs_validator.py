import logging
from typing import Dict, Optional, List, Any
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(project_id: str, private_key_id: str, private_key: str, 
                         client_email: str, client_id: str, client_cert_url: str,
                         folder_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate Google Docs credentials and folder access
    
    Args:
        project_id: Google Cloud project ID
        private_key_id: Service account private key ID
        private_key: Service account private key (PEM format)
        client_email: Service account client email
        client_id: Service account client ID
        client_cert_url: Service account certificate URL
        folder_id: Optional specific folder ID to test access
        
    Returns:
        Dict with status (success/error) and message
    """
    
    # Validate required parameters
    required_params = {
        "project_id": project_id,
        "private_key_id": private_key_id,
        "private_key": private_key,
        "client_email": client_email,
        "client_id": client_id,
        "client_cert_url": client_cert_url
    }
    
    missing_params = [param for param, value in required_params.items() if not value]
    if missing_params:
        logger.error(f'Missing required Google credentials: {", ".join(missing_params)}')
        return {
            "status": "error",
            "message": f"Missing required Google credentials: {', '.join(missing_params)}",
            "details": None
        }
    
    try:
        # Create service account credentials dictionary
        logger.info('Initializing Google service account credentials...')
        service_account_info = {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": private_key_id,
            "private_key": private_key,
            "client_email": client_email,
            "client_id": client_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": client_cert_url,
            "universe_domain": "googleapis.com"
        }

        # Set up Google Drive API scopes
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        
        # Create credentials from service account info
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)

        # Build the Drive API service
        logger.info('Building Google Drive service...')
        service = build('drive', 'v3', credentials=credentials)

        # Test connection by listing accessible files
        logger.info('Testing connection by listing accessible files...')
        
        # Determine query based on folder_id
        if folder_id:
            query = f"'{folder_id}' in parents and trashed=false"
            target_desc = f"folder {folder_id}"
        else:
            query = "sharedWithMe=true and trashed=false"
            target_desc = "shared files"
            
        # List files to verify access
        results = service.files().list(
            q=query,
            pageSize=10,  # Limit to 10 items for validation
            fields="files(id, name, mimeType, owners, shared)",
            orderBy="name"
        ).execute()
        
        items = results.get('files', [])
        file_count = len(items)
        logger.info(f'Found {file_count} items in {target_desc}')
        
        # We consider success even if no files are found, as long as the API call succeeded
        # because that validates the credentials
        
        # Extract first 5 files/folders for details
        file_details = []
        for item in items[:5]:
            is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
            owner = item.get('owners', [{'emailAddress': 'Unknown'}])[0].get('emailAddress', 'Unknown')
            file_details.append({
                "name": item.get('name', 'Unnamed'),
                "id": item.get('id'),
                "type": "folder" if is_folder else "file",
                "mime_type": item.get('mimeType'),
                "owner": owner
            })
        
        return {
            "status": "success",
            "message": f"Successfully authenticated with Google Drive and accessed {target_desc}",
            "details": {
                "service_account": client_email,
                "project_id": project_id,
                "folder_id": folder_id,
                "item_count": file_count,
                "items": file_details
            }
        }
    
    except Exception as e:
        logger.error(f'Error validating Google Docs connection: {str(e)}')
        error_message = str(e)
        
        # Enhance error message for common issues
        if "invalid_grant" in error_message.lower():
            error_message = f"Authentication error: {error_message}. Check if the service account has necessary permissions."
        elif "invalid_json" in error_message.lower():
            error_message = "Invalid JSON format for service account credentials."
        elif "file_not_found" in error_message.lower() or "notfound" in error_message.lower():
            error_message = f"Resource not found: {error_message}"
        elif "not found" in error_message.lower() and folder_id:
            error_message = f"Folder not found or no access: {error_message}. Check if the folder ID is correct and shared with the service account."
            
        return {
            "status": "error",
            "message": f"Google Docs connection failed: {error_message}",
            "details": {"error": error_message}
        }

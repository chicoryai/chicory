import logging
import json
from typing import Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(project_id: str, private_key_id: str, private_key: str,
                        client_email: str, client_id: str, client_cert_url: str,
                        dataset_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate BigQuery credentials and dataset access
    
    Args:
        project_id: Google Cloud project ID
        private_key_id: Service account private key ID
        private_key: Service account private key
        client_email: Service account client email
        client_id: Service account client ID
        client_cert_url: Service account client certificate URL
        dataset_id: Optional dataset ID to validate access
        
    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not project_id:
        logger.error('Google Cloud project ID not provided')
        return {
            "status": "error",
            "message": "Google Cloud project ID is required",
            "details": None
        }
        
    if not private_key:
        logger.error('Service account private key not provided')
        return {
            "status": "error",
            "message": "Service account private key is required",
            "details": None
        }
        
    if not client_email:
        logger.error('Service account client email not provided')
        return {
            "status": "error",
            "message": "Service account client email is required",
            "details": None
        }
    
    try:
        # Handle escaped newlines in private key (common when stored in env vars or JSON)
        private_key = private_key.replace("\\n", "\n")
        
        # Construct service account info dictionary
        # This matches the structure of a service account JSON file
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
            "client_x509_cert_url": client_cert_url
        }
        
        # Create credentials from service account info
        logger.info('Creating BigQuery credentials from service account info...')
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        
        # Create BigQuery client
        logger.info(f'Testing BigQuery connection for project: {project_id}')
        client = bigquery.Client(
            credentials=credentials,
            project=project_id
        )
        
        # Test connection by listing datasets
        logger.info('Testing BigQuery access by listing datasets...')
        datasets = list(client.list_datasets())
        dataset_count = len(datasets)
        dataset_ids = [dataset.dataset_id for dataset in datasets[:10]]  # Get up to 10 dataset IDs
        
        logger.info(f'Successfully listed {dataset_count} datasets')
        
        # Test specific dataset access if provided
        dataset_info = None
        table_names = []
        if dataset_id:
            logger.info(f'Testing access to specific dataset: {dataset_id}')
            try:
                # Get dataset details
                dataset = client.get_dataset(dataset_id)
                dataset_info = {
                    "dataset_id": dataset.dataset_id,
                    "location": dataset.location,
                    "created": dataset.created.isoformat() if dataset.created else None,
                    "description": dataset.description
                }
                
                # List tables in the dataset
                tables = list(client.list_tables(dataset_id))
                table_names = [table.table_id for table in tables[:10]]  # Get up to 10 table names
                logger.info(f'Successfully accessed dataset {dataset_id} with {len(tables)} tables')
                
            except Exception as e:
                logger.error(f'Dataset access failed: {str(e)}')
                return {
                    "status": "error",
                    "message": f"Cannot access dataset '{dataset_id}': {str(e)}",
                    "details": {
                        "project_id": project_id,
                        "dataset_count": dataset_count,
                        "available_datasets": dataset_ids
                    }
                }
        
        # Prepare success response with detailed info
        success_message = f"BigQuery connection successful for project {project_id}"
        if dataset_id and dataset_info:
            success_message += f" with access to dataset '{dataset_id}'"
        
        return {
            "status": "success",
            "message": success_message,
            "details": {
                "project_id": project_id,
                "service_account": client_email,
                "dataset_count": dataset_count,
                "available_datasets": dataset_ids,
                "dataset": dataset_info,
                "tables": table_names if table_names else None
            }
        }
        
    except ValueError as e:
        logger.error(f'Invalid service account credentials: {str(e)}')
        return {
            "status": "error",
            "message": f"Invalid service account credentials: {str(e)}",
            "details": None
        }
    except Exception as e:
        logger.error(f'BigQuery connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
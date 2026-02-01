import logging
import httpx
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(api_token: str, account_id: str, base_url: str = None, project_id: str = None, environment_id: str = None) -> Dict[str, Any]:
    """
    Validate DBT credentials and API access
    
    Args:
        api_token: DBT API token
        account_id: DBT account ID
        base_url: DBT base URL (optional)
        project_id: DBT project ID (optional)
        environment_id: DBT environment ID (optional)
        
    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not api_token:
        logger.error('DBT API token not provided')
        return {
            "status": "error",
            "message": "DBT API token is required",
            "details": None
        }
        
    if not account_id:
        logger.error('DBT account ID not provided')
        return {
            "status": "error",
            "message": "DBT account ID is required",
            "details": None
        }
    
    try:
        # Test DBT Cloud API connection
        logger.info(f'Testing DBT Cloud API connection for account: {account_id}')
        
        # Use DBT Cloud API to validate credentials
        # Default to cloud.getdbt.com if no base_url is provided
        api_base_url = base_url or "https://cloud.getdbt.com"
        if not api_base_url.startswith("http"):
            api_base_url = f"https://{api_base_url}"
        
        # Remove trailing slash if present
        api_base_url = api_base_url.rstrip('/')
        
        # Test API access by fetching account information
        api_url = f"{api_base_url}/api/v2/accounts/{account_id}/"
        
        headers = {
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f'Making API request to: {api_url}')
        
        response = httpx.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info('DBT Cloud API connection successful')
            
            account_data = response.json()
            account_name = account_data.get('data', {}).get('name', 'Unknown')
            
            success_message = f"DBT Cloud connection successful for account '{account_name}' ({account_id})"
            
            return {
                "status": "success",
                "message": success_message,
                "details": {
                    "account_id": account_id,
                    "account_name": account_name,
                    "base_url": api_base_url,
                    "project_id": project_id,
                    "environment_id": environment_id
                }
            }
        elif response.status_code == 401:
            logger.error('DBT Cloud API authentication failed')
            return {
                "status": "error",
                "message": "Invalid API token - authentication failed",
                "details": {"status_code": response.status_code}
            }
        elif response.status_code == 404:
            logger.error('DBT Cloud account not found')
            return {
                "status": "error", 
                "message": f"Account {account_id} not found or not accessible with this token",
                "details": {"status_code": response.status_code}
            }
        else:
            logger.error(f'DBT Cloud API request failed with status {response.status_code}')
            return {
                "status": "error",
                "message": f"API request failed with status {response.status_code}: {response.text}",
                "details": {"status_code": response.status_code, "response": response.text}
            }
        
    except httpx.RequestError as e:
        logger.error(f'HTTP request error: {str(e)}')
        return {
            "status": "error",
            "message": f"Network error connecting to DBT Cloud API: {str(e)}",
            "details": None
        }
    except Exception as e:
        logger.error(f'DBT connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "details": None
        }
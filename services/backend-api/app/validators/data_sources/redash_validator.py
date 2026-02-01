import logging
from typing import Dict, Any, Optional
from redash_toolbelt import Redash

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(base_url: str, api_key: str) -> Dict[str, Any]:
    """
    Validate Redash credentials and API access
    
    Args:
        base_url: Redash instance base URL
        api_key: Redash API key
        
    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not base_url:
        logger.error('Redash base URL not provided')
        return {
            "status": "error",
            "message": "Redash base URL is required",
            "details": None
        }
        
    if not api_key:
        logger.error('Redash API key not provided')
        return {
            "status": "error",
            "message": "Redash API key is required",
            "details": None
        }
    
    try:
        # Create Redash client
        logger.info(f'Testing Redash connection for instance: {base_url}')
        redash_client = Redash(base_url, api_key)
        
        # Test connection by getting user info
        logger.info('Testing Redash API access by retrieving user information...')
        user_info = redash_client.users()
        
        if not user_info:
            logger.error('Failed to retrieve user information from Redash API')
            return {
                "status": "error",
                "message": "Failed to authenticate with Redash API",
                "details": None
            }
        
        logger.info(f'Successfully authenticated as user: {user_info.get("name", "Unknown")}')
        
        # Test API access by listing dashboards
        try:
            logger.info('Testing Redash API access by listing dashboards...')
            dashboards = redash_client.dashboards()
            dashboard_count = len(dashboards) if dashboards else 0
            dashboard_names = [dashboard.get('name', 'Unnamed') for dashboard in dashboards[:10]] if dashboards else []
            
            logger.info(f'Successfully listed {dashboard_count} dashboards')
            
        except Exception as e:
            logger.warning(f'Could not list dashboards: {str(e)}')
            # Still consider authentication successful if we can get user info
            dashboard_count = 0
            dashboard_names = []
        
        # Prepare success response with detailed info
        success_message = f"Redash connection successful for instance {base_url}"
        
        return {
            "status": "success",
            "message": success_message,
            "details": {
                "base_url": base_url,
                "user_name": user_info.get("name"),
                "user_email": user_info.get("email"),
                "dashboard_count": dashboard_count,
                "dashboards": dashboard_names if dashboard_names else None
            }
        }
        
    except Exception as e:
        logger.error(f'Redash connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
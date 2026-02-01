import logging
from typing import Dict, Any, Optional
import looker_sdk

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(base_url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
    """
    Validate Looker credentials and API access
    
    Args:
        base_url: Looker instance base URL
        client_id: Looker API client ID
        client_secret: Looker API client secret
        
    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not base_url:
        logger.error('Looker base URL not provided')
        return {
            "status": "error",
            "message": "Looker base URL is required",
            "details": None
        }
        
    if not client_id:
        logger.error('Looker client ID not provided')
        return {
            "status": "error",
            "message": "Looker client ID is required",
            "details": None
        }
    
    if not client_secret:
        logger.error('Looker client secret not provided')
        return {
            "status": "error",
            "message": "Looker client secret is required",
            "details": None
        }
    
    try:
        # Create Looker SDK client
        logger.info(f'Testing Looker connection for instance: {base_url}')
        
        # Initialize the Looker SDK client
        sdk = looker_sdk.init40(
            config_settings={
                'base_url': base_url,
                'client_id': client_id,
                'client_secret': client_secret,
            }
        )
        
        # Test connection by getting current user info
        logger.info('Testing Looker API access by retrieving current user information...')
        current_user = sdk.me()
        
        if not current_user:
            logger.error('Failed to retrieve current user information from Looker API')
            return {
                "status": "error",
                "message": "Failed to authenticate with Looker API",
                "details": None
            }
        
        logger.info(f'Successfully authenticated as user: {current_user.display_name or current_user.email or "Unknown"}')
        
        # Test API access by listing available looks (queries)
        try:
            logger.info('Testing Looker API access by listing looks...')
            looks = sdk.all_looks(limit=10)
            look_count = len(looks) if looks else 0
            look_titles = [look.title for look in looks[:5] if look.title] if looks else []
            
            logger.info(f'Successfully listed {look_count} looks')
            
        except Exception as e:
            logger.warning(f'Could not list looks: {str(e)}')
            # Still consider authentication successful if we can get user info
            look_count = 0
            look_titles = []
        
        # Prepare success response with detailed info
        success_message = f"Looker connection successful for instance {base_url}"
        
        return {
            "status": "success",
            "message": success_message,
            "details": {
                "base_url": base_url,
                "user_display_name": current_user.display_name,
                "user_email": current_user.email,
                "user_id": current_user.id,
                "look_count": look_count,
                "sample_looks": look_titles if look_titles else None
            }
        }
        
    except Exception as e:
        logger.error(f'Looker connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
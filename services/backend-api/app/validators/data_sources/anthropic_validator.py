import logging
from typing import Dict, Any
import requests

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(api_key: str) -> Dict[str, Any]:
    """
    Validate Anthropic API key by making a test API call
    
    Args:
        api_key: Anthropic API key
        
    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not api_key:
        logger.error('Anthropic API key not provided')
        return {
            "status": "error",
            "message": "Anthropic API key is required",
            "details": None
        }
    
    try:
        # Test the API key by making a minimal request to the messages endpoint
        logger.info('Testing Anthropic API key...')
        
        api_url = 'https://api.anthropic.com/v1/messages'
        
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        
        # Minimal test payload
        payload = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 10,
            'messages': [
                {
                    'role': 'user',
                    'content': 'Hi'
                }
            ]
        }
        
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 401:
            logger.error('Authentication failed with Anthropic API')
            return {
                "status": "error",
                "message": "Authentication failed with Anthropic API. Please check your API key.",
                "details": None
            }
        
        if response.status_code == 403:
            logger.error('Access forbidden - API key may not have required permissions')
            return {
                "status": "error",
                "message": "Access forbidden. Your API key may not have the required permissions.",
                "details": None
            }
        
        if response.status_code == 429:
            logger.warning('Rate limit exceeded, but API key is valid')
            return {
                "status": "success",
                "message": "Anthropic API key is valid (rate limit reached during validation)",
                "details": {
                    "api_key_prefix": api_key[:10] + "..." if len(api_key) > 10 else "***",
                    "note": "Rate limit reached, but authentication successful"
                }
            }
        
        if response.status_code not in [200, 201]:
            logger.error(f'Failed to connect to Anthropic API. Status code: {response.status_code}')
            error_text = response.text
            return {
                "status": "error",
                "message": f"Failed to connect to Anthropic API. Status code: {response.status_code}",
                "details": {"error": error_text[:200]}
            }
        
        # Success - API key is valid
        response_data = response.json()
        logger.info('Successfully validated Anthropic API key')
        
        return {
            "status": "success",
            "message": "Anthropic API key validated successfully",
            "details": {
                "api_key_prefix": api_key[:10] + "..." if len(api_key) > 10 else "***",
                "model_tested": "claude-3-haiku-20240307"
            }
        }
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f'Connection error to Anthropic API: {str(e)}')
        return {
            "status": "error",
            "message": "Could not connect to Anthropic API. Please check your network connectivity.",
            "details": None
        }
    except requests.exceptions.Timeout as e:
        logger.error(f'Timeout connecting to Anthropic API: {str(e)}')
        return {
            "status": "error",
            "message": "Timeout connecting to Anthropic API. The server may be slow or unresponsive.",
            "details": None
        }
    except Exception as e:
        logger.error(f'Anthropic API validation error: {str(e)}')
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}",
            "details": None
        }

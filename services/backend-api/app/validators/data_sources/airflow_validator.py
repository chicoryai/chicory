import logging
from typing import Dict, Any
import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(base_url: str, username: str, password: str) -> Dict[str, Any]:
    """
    Validate Airflow credentials and API access
    
    Args:
        base_url: Airflow instance base URL
        username: Airflow username
        password: Airflow password
        
    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not base_url:
        logger.error('Airflow base URL not provided')
        return {
            "status": "error",
            "message": "Airflow base URL is required",
            "details": None
        }
        
    if not username:
        logger.error('Airflow username not provided')
        return {
            "status": "error",
            "message": "Airflow username is required",
            "details": None
        }
    
    if not password:
        logger.error('Airflow password not provided')
        return {
            "status": "error",
            "message": "Airflow password is required",
            "details": None
        }
    
    try:
        # Ensure base_url ends with appropriate path for API
        if not base_url.endswith('/'):
            base_url = base_url + '/'
        
        api_base_url = base_url + 'api/v1/'
        
        logger.info(f'Testing Airflow connection for instance: {base_url}')
        
        # Test connection by getting health status
        logger.info('Testing Airflow API access by checking health status...')
        health_url = api_base_url + 'health'
        
        response = requests.get(
            health_url,
            auth=HTTPBasicAuth(username, password),
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 401:
            logger.error('Authentication failed with Airflow API')
            return {
                "status": "error",
                "message": "Authentication failed with Airflow API. Please check your username and password.",
                "details": None
            }
        
        if response.status_code != 200:
            logger.error(f'Failed to connect to Airflow API. Status code: {response.status_code}')
            return {
                "status": "error",
                "message": f"Failed to connect to Airflow API. Status code: {response.status_code}",
                "details": None
            }
        
        health_data = response.json()
        logger.info(f'Successfully connected to Airflow API. Health status: {health_data}')
        
        # Test API access by listing DAGs
        try:
            logger.info('Testing Airflow API access by listing DAGs...')
            dags_url = api_base_url + 'dags'
            
            dag_response = requests.get(
                dags_url,
                auth=HTTPBasicAuth(username, password),
                timeout=30,
                headers={'Content-Type': 'application/json'},
                params={'limit': 10}  # Limit to 10 DAGs for testing
            )
            
            if dag_response.status_code == 200:
                dag_data = dag_response.json()
                dag_count = dag_data.get('total_entries', 0)
                dags = dag_data.get('dags', [])
                dag_names = [dag.get('dag_id', 'Unknown') for dag in dags[:5]]  # Get first 5 DAG names
                
                logger.info(f'Successfully listed {dag_count} DAGs')
                
                # Prepare success response with detailed info
                success_message = f"Airflow connection successful for instance {base_url}"
                
                return {
                    "status": "success",
                    "message": success_message,
                    "details": {
                        "base_url": base_url,
                        "username": username,
                        "dag_count": dag_count,
                        "sample_dags": dag_names if dag_names else None,
                        "health_status": health_data
                    }
                }
            else:
                logger.warning(f'Could not list DAGs: Status code {dag_response.status_code}')
                # Still consider authentication successful if we can access health endpoint
                return {
                    "status": "success",
                    "message": f"Airflow connection successful for instance {base_url}",
                    "details": {
                        "base_url": base_url,
                        "username": username,
                        "health_status": health_data,
                        "note": "Could not access DAGs endpoint, but authentication successful"
                    }
                }
                
        except Exception as e:
            logger.warning(f'Could not list DAGs: {str(e)}')
            # Still consider authentication successful if we can access health endpoint
            return {
                "status": "success",
                "message": f"Airflow connection successful for instance {base_url}",
                "details": {
                    "base_url": base_url,
                    "username": username,
                    "health_status": health_data,
                    "note": "Could not access DAGs endpoint, but authentication successful"
                }
            }
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f'Connection error to Airflow instance: {str(e)}')
        return {
            "status": "error",
            "message": f"Could not connect to Airflow instance at {base_url}. Please check the URL and network connectivity.",
            "details": None
        }
    except requests.exceptions.Timeout as e:
        logger.error(f'Timeout connecting to Airflow instance: {str(e)}')
        return {
            "status": "error",
            "message": f"Timeout connecting to Airflow instance at {base_url}. The server may be slow or unresponsive.",
            "details": None
        }
    except Exception as e:
        logger.error(f'Airflow connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
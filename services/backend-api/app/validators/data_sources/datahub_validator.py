import logging
from typing import Dict, Any, Optional
from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph
from requests.exceptions import HTTPError, RequestException, Timeout
import requests

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(base_url: str, api_key: str) -> Dict[str, Any]:
    """
    Validate Datahub credentials and API access
    
    Args:
        base_url: Datahub instance base URL
        api_key: Datahub API key
        
    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not base_url:
        logger.error('Datahub base URL not provided')
        return {
            "status": "error",
            "message": "Datahub base URL is required",
            "details": None
        }
        
    if not api_key:
        logger.error('Datahub API key not provided')
        return {
            "status": "error",
            "message": "Datahub API key is required",
            "details": None
        }
    
    try:
        # First, validate credentials using direct HTTP request with strict timeout
        logger.info(f'Testing Datahub connection for instance: {base_url}')

        # Normalize base_url - ensure it doesn't end with /
        base_url = base_url.rstrip('/')

        # Test authentication with a simple GraphQL query
        graphql_endpoint = f"{base_url}/api/graphql"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Simple query to test authentication
        query = {
            "query": "{ me { corpUser { username } } }"
        }

        logger.info('Testing authentication with direct HTTP request...')
        try:
            response = requests.post(
                graphql_endpoint,
                json=query,
                headers=headers,
                timeout=10  # 10 second timeout
            )

            # Check for authentication errors
            if response.status_code == 401:
                logger.error('Authentication failed: Invalid API key or token (401)')
                return {
                    "status": "error",
                    "message": "Authentication failed: Invalid API key or token",
                    "details": {"error_code": 401}
                }
            elif response.status_code == 403:
                logger.error('Authentication failed: Access forbidden (403)')
                return {
                    "status": "error",
                    "message": "Authentication failed: Access forbidden",
                    "details": {"error_code": 403}
                }
            elif response.status_code >= 400:
                logger.error(f'HTTP error {response.status_code}: {response.text}')
                return {
                    "status": "error",
                    "message": f"HTTP error {response.status_code}: {response.reason}",
                    "details": {"error_code": response.status_code}
                }

            response.raise_for_status()
            response_data = response.json()

            # Check if response has errors
            if "errors" in response_data:
                error_msg = response_data["errors"][0].get("message", "Unknown GraphQL error")
                logger.error(f'GraphQL error: {error_msg}')
                return {
                    "status": "error",
                    "message": f"GraphQL error: {error_msg}",
                    "details": None
                }

            logger.info('Successfully authenticated with Datahub API')

            # Get username if available
            username = None
            if "data" in response_data and response_data["data"] and "me" in response_data["data"]:
                me_data = response_data["data"]["me"]
                if me_data and "corpUser" in me_data and me_data["corpUser"]:
                    username = me_data["corpUser"].get("username")

        except Timeout:
            logger.error('Connection timeout: Could not reach Datahub server within 10 seconds')
            return {
                "status": "error",
                "message": "Connection timeout: Could not reach Datahub server within 10 seconds",
                "details": None
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Connection error: Could not connect to Datahub server - {str(e)}')
            return {
                "status": "error",
                "message": f"Connection error: Could not connect to Datahub server",
                "details": None
            }

        # Now try to get some metadata using the client (optional, for additional info)
        dataset_count = 0
        try:
            logger.info('Attempting to get dataset count...')
            config = DatahubClientConfig(
                server=base_url,
                token=api_key,
                timeout_sec=5,
                retry_max_times=0  # No retries
            )
            graph = DataHubGraph(config)

            # Try to get a small batch of datasets
            datasets = []
            urns_generator = graph.get_urns_by_filter(
                entity_types=["dataset"],
                batch_size=10
            )

            # Manually iterate with a limit to avoid hanging
            for i, urn in enumerate(urns_generator):
                if i >= 10:
                    break
                datasets.append(urn)

            dataset_count = len(datasets)
            logger.info(f'Successfully listed {dataset_count} datasets')

        except Exception as e:
            logger.warning(f'Could not list datasets: {str(e)}')
            # This is optional, so we don't fail if it doesn't work
            dataset_count = 0
            datasets = []

        # Prepare success response
        success_message = f"Datahub connection successful for instance {base_url}"

        return {
            "status": "success",
            "message": success_message,
            "details": {
                "base_url": base_url,
                "username": username,
                "dataset_count": dataset_count,
                "sample_datasets": datasets[:5] if datasets else None
            }
        }
        
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            logger.error('Authentication failed: Invalid API key or token')
            return {
                "status": "error",
                "message": "Authentication failed: Invalid API key or token",
                "details": {"error_code": 401}
            }
        logger.error(f'Datahub HTTP error: {str(e)}')
        return {
            "status": "error",
            "message": f"HTTP error: {str(e)}",
            "details": None
        }
    except Timeout:
        logger.error('Connection timeout: Could not reach Datahub server')
        return {
            "status": "error",
            "message": "Connection timeout: Could not reach Datahub server within 30 seconds",
            "details": None
        }
    except RequestException as e:
        logger.error(f'Datahub connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
    except Exception as e:
        logger.error(f'Datahub unexpected error: {str(e)}')
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "details": None
        }

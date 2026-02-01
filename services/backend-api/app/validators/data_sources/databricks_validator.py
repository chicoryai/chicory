import requests
import logging
import time
from typing import Dict, Optional, List, Any

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(access_token: str, host: str, catalog: Optional[str] = None,
                         schema: Optional[str] = None, http_path: Optional[str] = None,
                         workspace_url: Optional[str] = None, database: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate Databricks credentials and workspace/database access
    
    Args:
        access_token: Databricks personal access token
        host: Databricks host (e.g., 'dbc-abc123def-ghi.cloud.databricks.com')
        catalog: Optional catalog name to validate access
        schema: Optional schema name to validate access
        http_path: Optional HTTP path for SQL warehouse
        workspace_url: Optional workspace URL for specific workspace validation
        database: Optional database/schema name to validate access
        
    Returns:
        Dict with status (success/error) and message
    """
    if not access_token:
        logger.error('Databricks access token not provided')
        return {
            "status": "error",
            "message": "Databricks access token is required",
            "details": None
        }
        
    if not host:
        logger.error('Databricks host not provided')
        return {
            "status": "error",
            "message": "Databricks host is required",
            "details": None
        }
    
    if not http_path:
        logger.error('Databricks HTTP path not provided')
        return {
            "status": "error",
            "message": "Databricks HTTP path is required",
            "details": None
        }
    
    # Format the host URL if not already formatted
    if not host.startswith('https://'):
        host = f'https://{host}'
    
    # Remove trailing slash if present
    host = host.rstrip('/')
    
    # Set up headers for API requests
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        # First test: Basic authentication against the Databricks REST API
        logger.info('Testing Databricks authentication...')
        
        # We'll use the clusters/list API endpoint as a simple authentication test
        response = requests.get(f'{host}/api/2.0/clusters/list', headers=headers)
        
        if response.status_code != 200:
            logger.error(f'Authentication failed with status {response.status_code}')
            logger.error(f'Response: {response.text}')
            return {
                "status": "error",
                "message": f"Databricks authentication failed: {response.json().get('message', 'Unknown error')}",
                "details": response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            }
        
        # If we get here, authentication was successful
        clusters = response.json()
        logger.info(f'Authentication successful. Found {len(clusters.get("clusters", []))} clusters')
        
        # Second test (if database specified): Test database access using SQL warehouses
        if database:
            logger.info(f'Testing access to database: {database}')
            
            # First, get a list of SQL warehouses
            sql_endpoints_response = requests.get(f'{host}/api/2.0/sql/warehouses', headers=headers)
            
            if sql_endpoints_response.status_code != 200:
                logger.warning(f'Could not list SQL warehouses: {sql_endpoints_response.text}')
                return {
                    "status": "warning",
                    "message": f"Authentication successful, but unable to validate database '{database}' access: No SQL warehouses available.",
                    "details": {
                        "cluster_count": len(clusters.get("clusters", [])),
                        "database_validation": "skipped"
                    }
                }
            
            # Check if we have any SQL warehouses to test with
            warehouses = sql_endpoints_response.json().get("warehouses", [])
            if not warehouses:
                logger.warning('No SQL warehouses found to test database access')
                return {
                    "status": "warning",
                    "message": f"Authentication successful, but unable to validate database '{database}' access: No SQL warehouses available.",
                    "details": {
                        "cluster_count": len(clusters.get("clusters", [])),
                        "database_validation": "skipped"
                    }
                }
            
            # Take the first running warehouse
            running_warehouses = [w for w in warehouses if w.get("state") == "RUNNING"]
            warehouse_id = running_warehouses[0]["id"] if running_warehouses else warehouses[0]["id"]
            
            # Test a simple query against the database
            query_payload = {
                "warehouse_id": warehouse_id,
                "sql": f"SHOW TABLES IN {database}"
            }
            
            query_response = requests.post(f'{host}/api/2.0/sql/statements', 
                                         headers=headers, 
                                         json=query_payload)
            
            if query_response.status_code != 200:
                logger.error(f'Database access failed with status {query_response.status_code}')
                return {
                    "status": "error",
                    "message": f"Cannot access database '{database}': {query_response.json().get('message', 'Access denied')}",
                    "details": query_response.json() if query_response.headers.get('content-type', '').startswith('application/json') else None
                }
            
            # At this point, database access is confirmed
            result_state = query_response.json().get("result_state", "")
            if result_state != "CANCELED":
                logger.info(f'Successfully accessed database: {database}')
                
                # Wait for results if needed
                statement_id = query_response.json().get("statement_id")
                if statement_id and result_state != "FINISHED":
                    # Poll for results
                    max_retries = 5
                    while max_retries > 0 and result_state not in ["FINISHED", "FAILED", "CANCELED"]:
                        time.sleep(1)  # Give it a second to process
                        status_response = requests.get(f'{host}/api/2.0/sql/statements/{statement_id}', headers=headers)
                        if status_response.status_code == 200:
                            result_state = status_response.json().get("result_state", "")
                        max_retries -= 1
                
                # Try to get some table names for confirmation
                tables = []
                try:
                    if result_state == "FINISHED":
                        result_response = requests.get(f'{host}/api/2.0/sql/statements/{statement_id}/result', headers=headers)
                        if result_response.status_code == 200:
                            data = result_response.json().get("data", [])
                            if data:
                                tables = [row[0] for row in data][:5]  # Get up to 5 table names
                except Exception as e:
                    logger.warning(f"Error fetching table names: {str(e)}")
        
        # Prepare success response with detailed info
        return {
            "status": "success",
            "message": "Databricks connection successful" + (f" with access to database '{database}'" if database else ""),
            "details": {
                "host": host,
                "cluster_count": len(clusters.get("clusters", [])),
                "database": database,
                "tables": tables if 'tables' in locals() else None
            }
        }

    except Exception as e:
        logger.error(f'Databricks connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }

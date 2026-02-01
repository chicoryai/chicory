import snowflake.connector
import logging
from typing import Dict, Optional, List, Any
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(account: str, username: str, password: Optional[str] = None,
                         private_key: Optional[str] = None, private_key_passphrase: Optional[str] = None,
                         role: Optional[str] = None, warehouse: Optional[str] = None,
                         database: Optional[str] = None, schema: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate Snowflake credentials and warehouse/database access

    Args:
        account: Snowflake account identifier (e.g., 'abc12345.us-east-1')
        username: Snowflake username
        password: Optional Snowflake password (required if private_key is not provided)
        private_key: Optional private key for key pair authentication (required if password is not provided)
        private_key_passphrase: Optional passphrase for encrypted private key
        role: Optional Snowflake role to use for the session
        warehouse: Optional warehouse name to validate access
        database: Optional database name to validate access
        schema: Optional schema name to validate access

    Returns:
        Dict with status (success/error) and message
    """
    if not account:
        logger.error('Snowflake account not provided')
        return {
            "status": "error",
            "message": "Snowflake account is required",
            "details": None
        }

    if not username:
        logger.error('Snowflake username not provided')
        return {
            "status": "error",
            "message": "Snowflake username is required",
            "details": None
        }

    # Validate that either password or private_key is provided
    if not password and not private_key:
        logger.error('Neither password nor private_key provided')
        return {
            "status": "error",
            "message": "Either password or private_key is required for authentication",
            "details": None
        }
    
    # Validate required fields based on API requirements
    if not warehouse:
        logger.error('Snowflake warehouse not provided')
        return {
            "status": "error",
            "message": "Snowflake warehouse is required",
            "details": None
        }

    # Prepare connection parameters
    connection_params = {
        'account': account,
        'user': username
    }

    # Handle authentication: password or private key
    if private_key:
        logger.info('Using private key authentication')
        try:
            # Process the private key
            # Support both PEM format with headers and raw key content
            private_key_str = private_key.strip()

            # Handle various newline representations
            # 1. Handle escaped newlines from JSON (\\n -> \n)
            if '\\n' in private_key_str:
                private_key_str = private_key_str.replace('\\n', '\n')
                logger.debug('Replaced escaped newlines')

            # 2. Handle spaces between lines (sometimes keys are stored without proper newlines)
            # If we don't find proper newlines after BEGIN, try to fix formatting
            if '-----BEGIN' in private_key_str and '\n' not in private_key_str:
                # Key might be stored as a single line, add newlines at 64 character intervals
                logger.debug('Key appears to be single-line, attempting to reformat')
                lines = []
                # Split at BEGIN/END markers
                parts = private_key_str.split('-----')
                if len(parts) >= 5:  # Should have: '', 'BEGIN PRIVATE KEY', content, 'END PRIVATE KEY', ''
                    header = f"-----{parts[1]}-----"
                    content = parts[2].replace(' ', '').replace('\n', '').replace('\r', '')
                    footer = f"-----{parts[3]}-----"

                    # Split content into 64-character lines
                    content_lines = [content[i:i+64] for i in range(0, len(content), 64)]
                    private_key_str = header + '\n' + '\n'.join(content_lines) + '\n' + footer
                    logger.debug('Reformatted key with proper newlines')

            # If the key doesn't have PEM headers, add them
            if not private_key_str.startswith('-----BEGIN'):
                private_key_str = f"-----BEGIN PRIVATE KEY-----\n{private_key_str}\n-----END PRIVATE KEY-----"

            # Convert string to bytes
            private_key_bytes = private_key_str.encode('utf-8')

            # Load the private key with or without passphrase
            passphrase_bytes = None
            if private_key_passphrase:
                passphrase_bytes = private_key_passphrase.encode('utf-8')

            # Debug: Log first 100 chars of the processed key
            logger.debug(f'Processed key preview (first 100 chars): {repr(private_key_str[:100])}')
            logger.debug(f'Key has proper newlines: {chr(10) in private_key_str}')  # chr(10) is \n
            logger.debug(f'Key starts with: {private_key_str[:30]}')

            # Try loading the key - backend parameter is deprecated, try without it first
            p_key = None
            try:
                p_key = serialization.load_pem_private_key(
                    private_key_bytes,
                    password=passphrase_bytes
                )
                logger.info('Private key loaded successfully')
            except Exception as e:
                logger.warning(f'Failed to load key without backend: {str(e)}')
                # Fallback to using default_backend for older versions
                try:
                    p_key = serialization.load_pem_private_key(
                        private_key_bytes,
                        password=passphrase_bytes,
                        backend=default_backend()
                    )
                    logger.info('Private key loaded successfully with default_backend')
                except Exception as e2:
                    logger.error(f'Failed to load private key with both methods')
                    logger.error(f'Error details: {str(e2)}')
                    logger.error(f'Key length: {len(private_key_str)} chars')
                    logger.error(f'Key preview: {repr(private_key_str[:200])}...')
                    raise

            # Extract the private key in DER format (as required by Snowflake connector)
            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            connection_params['private_key'] = pkb
            logger.info('Private key processed successfully')
        except Exception as e:
            logger.error(f'Error processing private key: {str(e)}')
            return {
                "status": "error",
                "message": f"Failed to process private key: {str(e)}",
                "details": None
            }
    else:
        # Use password authentication
        logger.info('Using password authentication')
        connection_params['password'] = password

    # Add optional role parameter
    if role:
        connection_params['role'] = role
        logger.info(f'Using role: {role}')

    # Add warehouse parameter
    connection_params['warehouse'] = warehouse

    # Add optional database and schema
    if database:
        connection_params['database'] = database
    if schema:
        connection_params['schema'] = schema
    
    conn = None
    cursor = None
    
    try:
        # First test: Basic authentication and connection
        logger.info('Testing Snowflake authentication...')
        
        conn = snowflake.connector.connect(**connection_params)
        cursor = conn.cursor()
        
        # Test basic connection with a simple query
        cursor.execute("SELECT CURRENT_VERSION()")
        version_result = cursor.fetchone()
        
        if not version_result:
            logger.error('Failed to get Snowflake version')
            return {
                "status": "error",
                "message": "Failed to establish connection to Snowflake",
                "details": None
            }
        
        logger.info(f'Authentication successful. Snowflake version: {version_result[0]}')
        
        # Get current user and account info
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ACCOUNT(), CURRENT_ROLE()")
        user_info = cursor.fetchone()
        current_user, current_account, current_role = user_info if user_info else (None, None, None)
        
        # Test warehouse access if specified
        warehouse_info = None
        if warehouse:
            logger.info(f'Testing access to warehouse: {warehouse}')
            try:
                cursor.execute(f"USE WAREHOUSE {warehouse}")
                cursor.execute("SELECT CURRENT_WAREHOUSE()")
                warehouse_result = cursor.fetchone()
                warehouse_info = warehouse_result[0] if warehouse_result else None
                logger.info(f'Successfully accessed warehouse: {warehouse_info}')
            except Exception as e:
                logger.error(f'Warehouse access failed: {str(e)}')
                return {
                    "status": "error",
                    "message": f"Cannot access warehouse '{warehouse}': {str(e)}",
                    "details": {
                        "current_user": current_user,
                        "current_account": current_account,
                        "current_role": current_role
                    }
                }
        
        # Test database access if specified
        database_info = None
        tables = []
        if database:
            logger.info(f'Testing access to database: {database}')
            try:
                cursor.execute(f"USE DATABASE {database}")
                cursor.execute("SELECT CURRENT_DATABASE()")
                database_result = cursor.fetchone()
                database_info = database_result[0] if database_result else None
                
                # Try to list some tables for confirmation
                try:
                    cursor.execute(f"SHOW TABLES IN DATABASE {database}")
                    
                    table_results = cursor.fetchall()
                    if table_results:
                        # Snowflake SHOW TABLES returns multiple columns, table name is typically the second column
                        tables = [row[1] for row in table_results[:5]]  # Get up to 5 table names
                except Exception as e:
                    logger.warning(f"Error fetching table names: {str(e)}")
                
                logger.info(f'Successfully accessed database: {database_info}')
                
            except Exception as e:
                logger.error(f'Database access failed: {str(e)}')
                return {
                    "status": "error",
                    "message": f"Cannot access database '{database}': {str(e)}",
                    "details": {
                        "current_user": current_user,
                        "current_account": current_account,
                        "current_role": current_role,
                        "warehouse": warehouse_info
                    }
                }
        
        # Get available warehouses and databases for additional context
        available_warehouses = []
        available_databases = []
        
        try:
            cursor.execute("SHOW WAREHOUSES")
            warehouse_results = cursor.fetchall()
            if warehouse_results:
                available_warehouses = [row[0] for row in warehouse_results[:10]]  # Get up to 10 warehouse names
        except Exception as e:
            logger.warning(f"Error fetching available warehouses: {str(e)}")
        
        try:
            cursor.execute("SHOW DATABASES")
            database_results = cursor.fetchall()
            if database_results:
                available_databases = [row[1] for row in database_results[:10]]  # Get up to 10 database names
        except Exception as e:
            logger.warning(f"Error fetching available databases: {str(e)}")
        
        # Prepare success response with detailed info
        success_message = "Snowflake connection successful"
        if warehouse:
            success_message += f" with access to warehouse '{warehouse}'"
        if database:
            success_message += f" and database '{database}'"
        
        return {
            "status": "success",
            "message": success_message,
            "details": {
                "account": current_account,
                "user": current_user,
                "role": current_role,
                "warehouse": warehouse_info,
                "database": database_info,
                "tables": tables if tables else None,
                "available_warehouses": available_warehouses,
                "available_databases": available_databases,
                "version": version_result[0] if version_result else None
            }
        }

    except snowflake.connector.errors.DatabaseError as e:
        logger.error(f'Snowflake database error: {str(e)}')
        return {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "details": None
        }
    except snowflake.connector.errors.ProgrammingError as e:
        logger.error(f'Snowflake programming error: {str(e)}')
        return {
            "status": "error",
            "message": f"Programming error: {str(e)}",
            "details": None
        }
    except Exception as e:
        logger.error(f'Snowflake connection error: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
    finally:
        # Clean up connections
        if cursor:
            cursor.close()
        if conn:
            conn.close()

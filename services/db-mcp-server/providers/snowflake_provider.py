"""
Snowflake database provider implementation using the official Snowflake Python connector.
"""

import logging
from typing import Dict, List, Any, Optional
import snowflake.connector
from snowflake.connector import DictCursor
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from .base_provider import DatabaseProvider

logger = logging.getLogger(__name__)


class SnowflakeProvider(DatabaseProvider):
    """Snowflake database provider using the official Snowflake Python connector."""
    
    def __init__(self):
        super().__init__()
        self.connection = None
        self.warehouse: Optional[str] = None
    
    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """
        Initialize Snowflake connection using the Python connector.
        Supports both password-based and private key-based authentication.
        """
        try:
            logger.info(f"Initializing Snowflake provider with credentials keys: {list(credentials.keys())}")
            self.credentials = credentials

            # Extract connection parameters
            account = credentials.get("account")
            username = credentials.get("username")
            password = credentials.get("password")
            warehouse = credentials.get("warehouse")
            role = credentials.get("role")
            logger.info(f"Snowflake connection params - account: {account}, username: {username}, warehouse: {warehouse}, role : {role}")

            # Extract private key authentication parameters
            private_key_str = credentials.get("private_key")
            passphrase = credentials.get("passphrase")

            logger.info(f"Snowflake connection params - account: {account}, username: {username}, warehouse: {warehouse}, role: {role}")

            # Validate required parameters
            missing_params = []
            if not account:
                missing_params.append("account")
            if not username:
                missing_params.append("username")
            if not warehouse:
                missing_params.append("warehouse")

            # Ensure at least one authentication method is provided
            if not password and not private_key_str:
                missing_params.append("password or private_key")

            if missing_params:
                raise ValueError(f"Missing required Snowflake credentials: {', '.join(missing_params)}")
            
            # Store warehouse for later use
            self.warehouse = warehouse

            logger.info("Creating Snowflake connection...")
            
            # Prepare connection parameters (without database/schema - they'll be specified in queries)
            conn_params = {
                "account": account,
                "user": username,
                "warehouse": warehouse
            }

            # Add role if provided
            if role:
                conn_params["role"] = role

            # Handle authentication - prefer private key if provided
            if private_key_str:
                logger.info("Using private key authentication")
                try:
                    # Process the private key with robust handling
                    # Support both PEM format with headers and raw key content
                    private_key_str = private_key_str.strip()

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
                    if passphrase:
                        passphrase_bytes = passphrase.encode('utf-8')

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

                    conn_params["private_key"] = pkb
                    logger.info('Private key processed successfully and converted to DER format')
                except Exception as e:
                    logger.error(f'Error processing private key: {str(e)}')
                    raise ValueError(f"Failed to process private key: {str(e)}")
            elif password:
                logger.info("Using password authentication")
                conn_params["password"] = password

            # Create Snowflake connection
            self.connection = snowflake.connector.connect(**conn_params)

            self._initialized = True

            auth_method = "private_key" if private_key_str else "password"
            logger.info(f"Snowflake provider initialized successfully using {auth_method} for account: {account}, warehouse: {warehouse}")

        except Exception as e:
            logger.error(f"Failed to initialize Snowflake provider: {str(e)}", exc_info=True)
            raise
    
    async def execute_query(self, query: str, limit: Optional[int] = None, database: Optional[str] = None, schema: Optional[str] = None) -> Dict[str, Any]:
        """Execute a SQL query against Snowflake."""
        if not self._initialized or not self.connection:
            raise RuntimeError("Provider not initialized")
        
        try:
            # Set database and schema context if provided
            cursor = self.connection.cursor(DictCursor)
            
            if database:
                cursor.execute(f"USE DATABASE {database}")
            if schema:
                cursor.execute(f"USE SCHEMA {schema}")
            
            # Apply limit if specified and not already in query
            if limit and not any(keyword in query.upper() for keyword in ['LIMIT', 'TOP']):
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            # Execute query
            cursor.execute(query)
            
            # Fetch results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            cursor.close()
            
            return {
                "query": query,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }
            
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return {
                "error": str(e),
                "query": query,
                "rows": [],
                "columns": []
            }
    
    async def list_tables(self, database: str, schema: str) -> Dict[str, Any]:
        """
        List tables in a Snowflake database and schema.
        
        Args:
            database: Database name
            schema: Schema name
            
        Returns:
            Dictionary containing table list
        """
        try:
            # Use SHOW TABLES command for Snowflake
            query = f"SHOW TABLES IN {database}.{schema}"
            result = await self.execute_query(query, database=database, schema=schema)
            
            if "error" in result:
                return result
            
            # Parse SHOW TABLES results - Snowflake returns specific columns
            tables = []
            for row in result.get("rows", []):
                if isinstance(row, dict):
                    # Extract table name from SHOW TABLES result
                    table_name = row.get("name") or row.get("TABLE_NAME")
                    table_type = row.get("kind") or row.get("TABLE_TYPE", "TABLE")
                    if table_name:
                        tables.append({
                            "name": table_name,
                            "type": table_type
                        })
            
            return {
                "database": database,
                "schema": schema,
                "tables": tables,
                "table_count": len(tables)
            }
            
        except Exception as e:
            logger.error(f"Error listing tables in {database}.{schema}: {str(e)}")
            return {
                "error": str(e),
                "database": database,
                "schema": schema,
                "tables": [],
                "table_count": 0
            }
    
    async def describe_table(self, table_name: str, database: str, schema: str) -> Dict[str, Any]:
        """
        Get schema information for a Snowflake table.
        
        Args:
            table_name: Name of the table to describe
            database: Database name (required)
            schema: Schema name (required)
            
        Returns:
            Dictionary containing table schema information
        """
        try:
            # Create fully qualified table name
            if '.' not in table_name:
                qualified_name = f"{database}.{schema}.{table_name}"
            else:
                qualified_name = table_name
            
            # Use DESCRIBE TABLE command for Snowflake
            query = f"DESCRIBE TABLE {qualified_name}"
            result = await self.execute_query(query, database=database, schema=schema)
            
            if "error" in result:
                return {
                    "error": result["error"],
                    "table_name": qualified_name,
                    "columns": []
                }
            
            # Parse DESCRIBE TABLE results
            columns = []
            for row in result.get("rows", []):
                if isinstance(row, dict):
                    column_info = {
                        "name": row.get("name") or row.get("COLUMN_NAME"),
                        "type": row.get("type") or row.get("DATA_TYPE"),
                        "nullable": row.get("null?") or row.get("IS_NULLABLE"),
                        "default": row.get("default") or row.get("COLUMN_DEFAULT"),
                        "primary_key": row.get("primary key") or row.get("IS_PRIMARY_KEY")
                    }
                    columns.append(column_info)
            
            return {
                "table_name": qualified_name,
                "database": database,
                "schema": schema,
                "columns": columns,
                "column_count": len(columns)
            }
            
        except Exception as e:
            logger.error(f"Error describing table {table_name}: {str(e)}")
            return {
                "error": str(e),
                "table_name": table_name,
                "database": database,
                "schema": schema,
                "columns": []
            }
    
    async def sample_table(self, table_name: str, database: str, schema: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Sample data from a Snowflake table.
        
        Args:
            table_name: Name of the table to sample
            database: Database name (required)
            schema: Schema name (required)
            limit: Number of rows to sample (default: 10)
            
        Returns:
            Dictionary containing sample data
        """
        try:
            # Create fully qualified table name
            if '.' not in table_name:
                qualified_name = f"{database}.{schema}.{table_name}"
            else:
                qualified_name = table_name
            
            # Set default limit
            if limit is None:
                limit = 10
            
            query = f"SELECT * FROM {qualified_name} LIMIT {limit}"
            result = await self.execute_query(query, database=database, schema=schema)
            
            return {
                "table_name": qualified_name,
                "database": database,
                "schema": schema,
                "sample_size": limit,
                "columns": result.get("columns", []),
                "rows": result.get("rows", []),
                "actual_rows": len(result.get("rows", []))
            }
            
        except Exception as e:
            logger.error(f"Error sampling table {table_name}: {str(e)}")
            return {
                "error": str(e),
                "table_name": table_name,
                "database": database,
                "schema": schema,
                "sample_size": limit,
                "columns": [],
                "rows": [],
                "actual_rows": 0
            }
    
    async def test_connection(self) -> bool:
        """Test the Snowflake connection."""
        try:
            if not self._initialized or not self.connection:
                return False
            
            # Simple test query
            result = await self.execute_query("SELECT 1 as test")
            return "error" not in result and len(result.get("rows", [])) > 0
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up Snowflake connection and resources."""
        try:
            # Close Snowflake connection
            if self.connection:
                self.connection.close()
                self.connection = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        finally:
            await super().cleanup()

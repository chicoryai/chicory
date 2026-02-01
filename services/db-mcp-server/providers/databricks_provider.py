"""
Databricks database provider implementation using the official Databricks Python SDK.
"""

import logging
from typing import Dict, List, Any, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementExecutionAPI

from .base_provider import DatabaseProvider

logger = logging.getLogger(__name__)


class DatabricksProvider(DatabaseProvider):
    """Databricks database provider using the official Databricks Python SDK."""
    
    def __init__(self):
        super().__init__()
        self.workspace_client: Optional[WorkspaceClient] = None
        self.warehouse_id: Optional[str] = None
    
    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """Initialize Databricks connection using the Python SDK."""
        try:
            self.credentials = credentials
            
            # Extract connection parameters
            host = credentials["host"]
            http_path = credentials["http_path"]
            access_token = credentials["access_token"]
            
            # Validate required parameters
            if not all([host, http_path, access_token]):
                raise ValueError("Missing required Databricks credentials: host, http_path, access_token")
            
            # Extract warehouse ID from http_path
            # http_path format: /sql/1.0/warehouses/{warehouse_id}
            if "/warehouses/" in http_path:
                self.warehouse_id = http_path.split("/warehouses/")[-1]
            else:
                raise ValueError(f"Invalid http_path format: {http_path}. Expected format: /sql/1.0/warehouses/{{warehouse_id}}")
            
            # Create Databricks workspace client directly (no threading needed)
            self.workspace_client = self._create_workspace_client(host, access_token)
            
            self._initialized = True
            
            logger.info(f"Databricks provider initialized successfully for host: {host}, warehouse: {self.warehouse_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Databricks provider: {str(e)}")
            raise
    
    def _create_workspace_client(self, host: str, access_token: str) -> WorkspaceClient:
        """Create Databricks WorkspaceClient."""
        # Ensure host has https:// prefix
        if not host.startswith("https://"):
            host = f"https://{host}"
        
        return WorkspaceClient(
            host=host,
            token=access_token
        )
    
    async def execute_query(self, query: str, limit: Optional[int] = None, catalog: str = None, schema: str = None) -> Dict[str, Any]:
        """Execute a SQL query against Databricks using the Python SDK."""
        if not self._initialized or not self.workspace_client:
            raise RuntimeError("Provider not initialized")
        
        try:
            # Apply limit only for SELECT statements and if not already present
            query_upper = query.strip().upper()
            if limit and query_upper.startswith('SELECT') and not any(keyword in query_upper for keyword in ['LIMIT', 'TOP']):
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            # Execute query directly (no threading needed)
            result = self._execute_query_sync(query, catalog, schema)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return {
                "error": str(e),
                "query": query,
                "rows": [],
                "columns": []
            }
    
    def _execute_query_sync(self, query: str, catalog: str, schema: str) -> Dict[str, Any]:
        """Execute query synchronously using Databricks SDK (runs in thread pool)."""
        try:
            # Execute SQL statement using the Databricks SDK
            response = self.workspace_client.statement_execution.execute_statement(
                statement=query,
                warehouse_id=self.warehouse_id,
                catalog=catalog,
                schema=schema,
                wait_timeout="30s"
            )
            
            # Extract results from the response
            if response.result and response.result.data_array:
                # Get column names from manifest
                columns = []
                if response.manifest and response.manifest.schema and response.manifest.schema.columns:
                    columns = [col.name for col in response.manifest.schema.columns]
                
                # Convert data array to list of dictionaries
                result_rows = []
                for row_data in response.result.data_array:
                    row_dict = {}
                    for i, value in enumerate(row_data):
                        column_name = columns[i] if i < len(columns) else f"col_{i}"
                        # Handle None values and convert complex types to string for JSON serialization
                        if value is None:
                            row_dict[column_name] = None
                        elif isinstance(value, (bytes, bytearray)):
                            row_dict[column_name] = str(value)
                        else:
                            row_dict[column_name] = value
                    result_rows.append(row_dict)
                
                return {
                    "query": query,
                    "columns": columns,
                    "rows": result_rows,
                    "row_count": len(result_rows)
                }
            else:
                # No data returned (e.g., DDL statements)
                return {
                    "query": query,
                    "columns": [],
                    "rows": [],
                    "row_count": 0
                }
                
        except Exception as e:
            logger.error(f"Error in _execute_query_sync: {str(e)}")
            raise
    
    async def list_tables(self, catalog: str, schema_name: str) -> Dict[str, Any]:
        """List tables using SHOW TABLES command."""
        try:
            # Build SHOW TABLES query with catalog and schema
            query = f"SHOW TABLES IN {catalog}.{schema_name}"
            
            result = await self.execute_query(query, catalog=catalog, schema=schema_name)
            
            # Extract table names from result
            tables = []
            if "rows" in result:
                for row in result["rows"]:
                    # SHOW TABLES returns columns like: database, tableName, isTemporary
                    table_name = row.get("tableName") or row.get("table_name")
                    if table_name:
                        tables.append({
                            "name": table_name,
                            "schema": row.get("database") or schema_name,
                            "type": "TABLE"  # Could be enhanced to detect VIEW vs TABLE
                        })
            
            return {
                "schema": schema_name,
                "tables": tables,
                "count": len(tables)
            }
            
        except Exception as e:
            logger.error(f"Error listing tables: {str(e)}")
            return {
                "error": str(e),
                "schema": schema_name,
                "tables": [],
                "count": 0
            }
    
    async def describe_table(self, table_name: str, catalog: str, schema_name: str) -> Dict[str, Any]:
        """Describe table schema using DESCRIBE command."""
        try:
            # Build fully qualified table name
            qualified_name = f"{catalog}.{schema_name}.{table_name}"
            
            query = f"DESCRIBE {qualified_name}"
            result = await self.execute_query(query, catalog=catalog, schema=schema_name)
            
            # Parse DESCRIBE output
            columns = []
            if "rows" in result:
                for row in result["rows"]:
                    col_name = row.get("col_name") or row.get("column_name")
                    data_type = row.get("data_type") or row.get("type")
                    comment = row.get("comment", "")
                    
                    if col_name and data_type:
                        columns.append({
                            "name": col_name,
                            "type": data_type,
                            "comment": comment,
                            "nullable": True  # Databricks doesn't provide nullable info in DESCRIBE
                        })
            
            return {
                "table_name": qualified_name,
                "columns": columns,
                "column_count": len(columns)
            }
            
        except Exception as e:
            logger.error(f"Error describing table {table_name}: {str(e)}")
            return {
                "error": str(e),
                "table_name": table_name,
                "columns": [],
                "column_count": 0
            }
    
    async def sample_table(self, table_name: str, catalog: str, schema_name: str, 
                          limit: Optional[int] = None) -> Dict[str, Any]:
        """Sample data from a table."""
        try:
            # Build fully qualified table name
            qualified_name = f"{catalog}.{schema_name}.{table_name}"
            
            # Set default limit
            if limit is None:
                limit = 10
            
            query = f"SELECT * FROM {qualified_name} LIMIT {limit}"
            result = await self.execute_query(query, catalog=catalog, schema=schema_name)
            
            return {
                "table_name": qualified_name,
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
                "sample_size": limit,
                "columns": [],
                "rows": [],
                "actual_rows": 0
            }
    
    async def test_connection(self) -> bool:
        """Test the Databricks connection."""
        try:
            if not self._initialized or not self.workspace_client:
                return False
            
            # Simple test query with default catalog and schema
            result = await self.execute_query("SELECT 1 as test", catalog="main", schema="default")
            return "error" not in result and len(result.get("rows", [])) > 0
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up Databricks connection and resources."""
        try:
            # The Databricks SDK WorkspaceClient doesn't require explicit cleanup
            # but we'll clear our reference
            if self.workspace_client:
                self.workspace_client = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        finally:
            await super().cleanup()

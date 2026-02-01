"""
Redshift database provider implementation using the psycopg2 PostgreSQL adapter.
"""

import logging
import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional

from .base_provider import DatabaseProvider

logger = logging.getLogger(__name__)


class RedshiftProvider(DatabaseProvider):
    """Redshift database provider using psycopg2."""
    
    def __init__(self):
        super().__init__()
        self.connection = None
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.database: Optional[str] = None
        self.user: Optional[str] = None
        self.password: Optional[str] = None
    
    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """Initialize Redshift connection using provided credentials."""
        try:
            self.credentials = credentials
            
            # Extract connection parameters
            self.host = credentials.get("host")
            self.port = credentials.get("port", 5439)  # Default Redshift port
            self.database = credentials.get("database")
            self.user = credentials.get("user")
            self.password = credentials.get("password")
            
            # Validate required fields
            if not all([self.host, self.database, self.user, self.password]):
                raise ValueError("Missing required Redshift credentials: host, database, user, or password")
            
            # Create connection
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=30
            )
            
            # Set autocommit for read operations
            self.connection.autocommit = True
            
            self._initialized = True
            logger.info(f"Redshift provider initialized successfully for {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redshift provider: {e}")
            self._initialized = False
            raise
    
    async def test_connection(self) -> bool:
        """Test the Redshift connection by executing a simple query."""
        try:
            if not self.connection:
                return False
            
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info("Redshift connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Redshift connection test failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up Redshift resources."""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
            
            await super().cleanup()
            logger.info("Redshift provider cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during Redshift provider cleanup: {e}")
    
    async def execute_query(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """
        Execute a SQL query against Redshift.
        
        Args:
            query: SQL query to execute
            limit: Maximum number of rows to return
            
        Returns:
            Dictionary with query results and metadata
        """
        try:
            if not self.connection:
                raise RuntimeError("Redshift connection not initialized")
            
            # Add limit to query if not already present
            query_lower = query.lower().strip()
            if not query_lower.endswith(';'):
                query = query.strip()
            if 'limit' not in query_lower and not query_lower.startswith(('insert', 'update', 'delete', 'create', 'drop', 'alter')):
                if query.endswith(';'):
                    query = query[:-1] + f" LIMIT {limit};"
                else:
                    query = query + f" LIMIT {limit}"
            
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query)
                
                # For SELECT queries, fetch results
                if cursor.description:
                    rows = cursor.fetchall()
                    columns = [desc.name for desc in cursor.description]
                    
                    # Convert rows to list of dictionaries
                    result_rows = []
                    for row in rows:
                        row_dict = {}
                        for key, value in row.items():
                            if hasattr(value, 'isoformat'):  # datetime objects
                                row_dict[key] = value.isoformat()
                            else:
                                row_dict[key] = value
                        result_rows.append(row_dict)
                    
                    return {
                        "rows": result_rows,
                        "columns": columns,
                        "row_count": len(result_rows)
                    }
                else:
                    # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                    return {
                        "rows": [],
                        "columns": [],
                        "row_count": cursor.rowcount if cursor.rowcount > 0 else 0,
                        "affected_rows": cursor.rowcount if cursor.rowcount > 0 else 0
                    }
            
        except Exception as e:
            logger.error(f"Error executing Redshift query: {e}")
            return {"error": str(e)}
    
    async def list_tables(self, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        List tables in Redshift schemas.
        
        Args:
            schema_name: Schema name (optional, lists from public schema if not provided)
            
        Returns:
            Dictionary with list of tables and metadata
        """
        try:
            if not self.connection:
                raise RuntimeError("Redshift connection not initialized")
            
            schema = schema_name or "public"
            
            # Query to list tables in the specified schema
            query = """
                SELECT schemaname, tablename, tableowner, tablespace, hasindexes, hasrules, hastriggers
                FROM pg_tables
                WHERE schemaname = %s
                ORDER BY tablename
            """
            
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (schema,))
                results = cursor.fetchall()
                
                tables = []
                for row in results:
                    tables.append({
                        "schema": row["schemaname"],
                        "name": row["tablename"],
                        "owner": row["tableowner"],
                        "tablespace": row["tablespace"],
                        "has_indexes": row["hasindexes"],
                        "has_rules": row["hasrules"],
                        "has_triggers": row["hastriggers"],
                        "type": "TABLE"
                    })
                
                return {
                    "tables": tables,
                    "schema": schema,
                    "count": len(tables)
                }
            
        except Exception as e:
            logger.error(f"Error listing Redshift tables: {e}")
            return {"error": str(e)}
    
    async def describe_table(self, table_name: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a Redshift table including schema.
        
        Args:
            table_name: Name of the table to describe
            schema_name: Schema name (optional, uses public if not provided)
            
        Returns:
            Dictionary with table metadata and schema information
        """
        try:
            if not self.connection:
                raise RuntimeError("Redshift connection not initialized")
            
            schema = schema_name or "public"
            
            # Query to get column information
            query = """
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """
            
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (schema, table_name))
                columns = cursor.fetchall()
                
                if not columns:
                    return {"error": f"Table {schema}.{table_name} not found"}
                
                # Format column information
                column_info = []
                for col in columns:
                    col_dict = {
                        "name": col["column_name"],
                        "type": col["data_type"],
                        "nullable": col["is_nullable"] == "YES",
                        "default": col["column_default"],
                        "position": col["ordinal_position"]
                    }
                    
                    # Add type-specific information
                    if col["character_maximum_length"]:
                        col_dict["max_length"] = col["character_maximum_length"]
                    if col["numeric_precision"]:
                        col_dict["precision"] = col["numeric_precision"]
                    if col["numeric_scale"]:
                        col_dict["scale"] = col["numeric_scale"]
                    
                    column_info.append(col_dict)
                
                return {
                    "table_name": f"{schema}.{table_name}",
                    "schema": schema,
                    "columns": column_info,
                    "column_count": len(column_info)
                }
            
        except Exception as e:
            logger.error(f"Error describing Redshift table {table_name}: {e}")
            return {"error": str(e)}
    
    async def sample_table(self, table_name: str, schema_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Get a sample of data from a Redshift table.
        
        Args:
            table_name: Name of the table to sample
            schema_name: Schema name (optional, uses public if not provided)
            limit: Maximum number of rows to return
            
        Returns:
            Dictionary with sample data and metadata
        """
        try:
            if not self.connection:
                raise RuntimeError("Redshift connection not initialized")
            
            schema = schema_name or "public"
            qualified_table = f'"{schema}"."{table_name}"'
            
            # Execute sample query
            query = f"SELECT * FROM {qualified_table} LIMIT {limit}"
            
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                columns = [desc.name for desc in cursor.description] if cursor.description else []
                
                # Convert results to list of dictionaries
                rows = []
                for row in results:
                    row_dict = {}
                    for key, value in row.items():
                        if hasattr(value, 'isoformat'):  # datetime objects
                            row_dict[key] = value.isoformat()
                        else:
                            row_dict[key] = value
                    rows.append(row_dict)
                
                return {
                    "table_name": f"{schema}.{table_name}",
                    "schema": schema,
                    "sample_size": len(rows),
                    "actual_rows": len(rows),
                    "limit": limit,
                    "columns": columns,
                    "rows": rows
                }
            
        except Exception as e:
            logger.error(f"Error sampling Redshift table {table_name}: {e}")
            return {"error": str(e)}
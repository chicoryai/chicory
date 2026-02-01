"""
BigQuery database provider implementation using the Google Cloud BigQuery Python SDK.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account

from .base_provider import DatabaseProvider

logger = logging.getLogger(__name__)


class BigQueryProvider(DatabaseProvider):
    """BigQuery database provider using the Google Cloud BigQuery Python SDK."""
    
    def __init__(self):
        super().__init__()
        self.client: Optional[bigquery.Client] = None
        self.project_id: Optional[str] = None
    
    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """Initialize BigQuery connection using service account credentials."""
        try:
            self.credentials = credentials
            
            # Handle both service account JSON and individual credential fields
            if isinstance(credentials, dict) and "type" in credentials and credentials["type"] == "service_account":
                # Service account JSON format
                service_account_info = credentials
                self.project_id = service_account_info["project_id"]
            else:
                # Individual credential fields
                service_account_info = credentials.get("service_account_info")
                if not service_account_info:
                    raise ValueError("Missing service_account_info in BigQuery credentials")
                
                if isinstance(service_account_info, str):
                    service_account_info = json.loads(service_account_info)
                
                self.project_id = service_account_info["project_id"]
            
            # Create credentials from service account info
            creds = service_account.Credentials.from_service_account_info(service_account_info)
            
            # Create BigQuery client
            self.client = bigquery.Client(credentials=creds, project=self.project_id)
            
            self._initialized = True
            logger.info(f"BigQuery provider initialized successfully for project: {self.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery provider: {e}")
            self._initialized = False
            raise
    
    async def test_connection(self) -> bool:
        """Test the BigQuery connection by listing datasets."""
        try:
            if not self.client:
                return False
            
            # Try to list datasets to test connection
            datasets = list(self.client.list_datasets(max_results=1))
            logger.info("BigQuery connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"BigQuery connection test failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up BigQuery resources."""
        try:
            if self.client:
                # BigQuery client doesn't need explicit cleanup
                self.client = None
            
            await super().cleanup()
            logger.info("BigQuery provider cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during BigQuery provider cleanup: {e}")
    
    async def list_tables(self, dataset: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List tables in BigQuery datasets.
        
        Args:
            dataset: Specific dataset to list tables from. If None, lists from all datasets.
            limit: Maximum number of tables to return
            
        Returns:
            List of table information dictionaries
        """
        try:
            if not self.client:
                raise RuntimeError("BigQuery client not initialized")
            
            tables = []
            
            if dataset:
                # List tables from specific dataset
                dataset_ref = self.client.dataset(dataset, project=self.project_id)
                try:
                    dataset_tables = self.client.list_tables(dataset_ref, max_results=limit)
                    for table in dataset_tables:
                        tables.append({
                            "project_id": table.project,
                            "dataset_id": table.dataset_id,
                            "table_id": table.table_id,
                            "table_type": table.table_type,
                            "full_table_id": f"{table.project}.{table.dataset_id}.{table.table_id}",
                            "created": table.created.isoformat() if hasattr(table, 'created') and table.created else None,
                            "modified": table.modified.isoformat() if hasattr(table, 'modified') and table.modified else None,
                            "num_rows": table.num_rows if hasattr(table, 'num_rows') else None,
                            "num_bytes": table.num_bytes if hasattr(table, 'num_bytes') else None
                        })
                except Exception as e:
                    logger.warning(f"Could not list tables from dataset {dataset}: {e}")
            else:
                # List tables from all datasets
                datasets = self.client.list_datasets(project=self.project_id)
                table_count = 0
                
                for dataset_item in datasets:
                    if table_count >= limit:
                        break
                    
                    try:
                        dataset_tables = self.client.list_tables(dataset_item.reference, max_results=limit - table_count)
                        for table in dataset_tables:
                            if table_count >= limit:
                                break
                            
                            tables.append({
                                "project_id": table.project,
                                "dataset_id": table.dataset_id,
                                "table_id": table.table_id,
                                "table_type": table.table_type,
                                "full_table_id": f"{table.project}.{table.dataset_id}.{table.table_id}",
                                "created": table.created.isoformat() if hasattr(table, 'created') and table.created else None,
                                "modified": table.modified.isoformat() if hasattr(table, 'modified') and table.modified else None,
                                "num_rows": table.num_rows if hasattr(table, 'num_rows') else None,
                                "num_bytes": table.num_bytes if hasattr(table, 'num_bytes') else None
                            })
                            table_count += 1
                    except Exception as e:
                        logger.warning(f"Could not list tables from dataset {dataset_item.dataset_id}: {e}")
            
            logger.info(f"Listed {len(tables)} tables from BigQuery")
            return tables
            
        except Exception as e:
            logger.error(f"Error listing BigQuery tables: {e}")
            raise
    
    async def describe_table(self, table_id: str, dataset: str) -> Dict[str, Any]:
        """
        Get detailed information about a BigQuery table including schema.
        
        Args:
            table_id: Table identifier (can be full path project.dataset.table or just table name)
            dataset: Dataset name (required)
            
        Returns:
            Dictionary with table metadata and schema information
        """
        try:
            if not self.client:
                raise RuntimeError("BigQuery client not initialized")
            
            # Parse table reference
            if "." in table_id and table_id.count(".") >= 2:
                # Full table reference: project.dataset.table
                table_ref = self.client.get_table(table_id)
            else:
                # Just table name, use provided dataset
                table_ref = self.client.get_table(f"{self.project_id}.{dataset}.{table_id}")
            
            # Get table metadata
            table_info = {
                "project_id": table_ref.project,
                "dataset_id": table_ref.dataset_id,
                "table_id": table_ref.table_id,
                "full_table_id": f"{table_ref.project}.{table_ref.dataset_id}.{table_ref.table_id}",
                "table_type": table_ref.table_type,
                "created": table_ref.created.isoformat() if table_ref.created else None,
                "modified": table_ref.modified.isoformat() if table_ref.modified else None,
                "num_rows": table_ref.num_rows,
                "num_bytes": table_ref.num_bytes,
                "description": table_ref.description,
                "location": table_ref.location,
                "schema": []
            }
            
            # Get schema information
            for field in table_ref.schema:
                field_info = {
                    "name": field.name,
                    "field_type": field.field_type,
                    "mode": field.mode,
                    "description": field.description
                }
                
                # Handle nested fields
                if field.fields:
                    field_info["fields"] = self._parse_nested_fields(field.fields)
                
                table_info["schema"].append(field_info)
            
            logger.info(f"Described BigQuery table: {table_ref.full_table_id}")
            return table_info
            
        except Exception as e:
            logger.error(f"Error describing BigQuery table {table_id}: {e}")
            raise
    
    def _parse_nested_fields(self, fields) -> List[Dict[str, Any]]:
        """Parse nested schema fields recursively."""
        nested_fields = []
        for field in fields:
            field_info = {
                "name": field.name,
                "field_type": field.field_type,
                "mode": field.mode,
                "description": field.description
            }
            
            if field.fields:
                field_info["fields"] = self._parse_nested_fields(field.fields)
            
            nested_fields.append(field_info)
        
        return nested_fields
    
    async def sample_table(self, table_id: str, dataset: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get a sample of data from a BigQuery table.
        
        Args:
            table_id: Table identifier (can be full path project.dataset.table or just table name)
            dataset: Dataset name (required)
            limit: Maximum number of rows to return
            
        Returns:
            Dictionary with sample data and metadata
        """
        try:
            if not self.client:
                raise RuntimeError("BigQuery client not initialized")
            
            # Parse table reference
            if "." in table_id and table_id.count(".") >= 2:
                # Full table reference: project.dataset.table
                full_table_id = table_id
            else:
                # Just table name, use provided dataset
                full_table_id = f"{self.project_id}.{dataset}.{table_id}"
            
            # Execute sample query
            query = f"SELECT * FROM `{full_table_id}` LIMIT {limit}"
            query_job = self.client.query(query)
            results = query_job.result()
            
            # Convert results to list of dictionaries
            rows = []
            for row in results:
                # Convert Row to dictionary, handling various data types
                row_dict = {}
                for key, value in row.items():
                    if hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[key] = value.isoformat()
                    elif isinstance(value, (list, dict)):  # complex types
                        row_dict[key] = str(value)
                    else:
                        row_dict[key] = value
                rows.append(row_dict)
            
            # Get column information
            columns = []
            if results.schema:
                for field in results.schema:
                    columns.append({
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode
                    })
            
            sample_info = {
                "table_id": full_table_id,
                "sample_size": len(rows),
                "limit": limit,
                "columns": columns,
                "rows": rows,
                "total_bytes_processed": query_job.total_bytes_processed,
                "job_id": query_job.job_id
            }
            
            logger.info(f"Sampled {len(rows)} rows from BigQuery table: {full_table_id}")
            return sample_info
            
        except Exception as e:
            logger.error(f"Error sampling BigQuery table {table_id}: {e}")
            raise
    
    async def query(self, sql: str, limit: int = 100, dataset: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a SQL query against BigQuery.

        Args:
            sql: SQL query to execute
            limit: Maximum number of rows to return
            dataset: Optional default dataset for unqualified table names

        Returns:
            Dictionary with query results and metadata
        """
        try:
            if not self.client:
                raise RuntimeError("BigQuery client not initialized")

            # Add limit to query if not already present
            sql_lower = sql.lower().strip()
            if not sql_lower.endswith(';'):
                sql = sql.strip()
            if 'limit' not in sql_lower:
                if sql.endswith(';'):
                    sql = sql[:-1] + f" LIMIT {limit};"
                else:
                    sql = sql + f" LIMIT {limit}"

            # Configure query with default dataset if provided
            job_config = None
            if dataset:
                job_config = bigquery.QueryJobConfig(
                    default_dataset=f"{self.project_id}.{dataset}"
                )

            # Execute query
            query_job = self.client.query(sql, job_config=job_config)
            results = query_job.result()
            
            # Convert results to list of dictionaries
            rows = []
            for row in results:
                row_dict = {}
                for key, value in row.items():
                    if hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[key] = value.isoformat()
                    elif isinstance(value, (list, dict)):  # complex types
                        row_dict[key] = str(value)
                    else:
                        row_dict[key] = value
                rows.append(row_dict)
            
            # Get column information
            columns = []
            if results.schema:
                for field in results.schema:
                    columns.append({
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode
                    })
            
            query_info = {
                "sql": sql,
                "row_count": len(rows),
                "columns": columns,
                "rows": rows,
                "total_bytes_processed": query_job.total_bytes_processed,
                "total_bytes_billed": query_job.total_bytes_billed,
                "job_id": query_job.job_id,
                "creation_time": query_job.created.isoformat() if query_job.created else None,
                "started_time": query_job.started.isoformat() if query_job.started else None,
                "ended_time": query_job.ended.isoformat() if query_job.ended else None
            }
            
            logger.info(f"Executed BigQuery query, returned {len(rows)} rows")
            return query_info
            
        except Exception as e:
            logger.error(f"Error executing BigQuery query: {e}")
            raise

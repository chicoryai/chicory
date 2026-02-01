#!/usr/bin/env python3
"""
DB MCP Server - A Model Context Protocol server for database operations using FastMCP.

Provides tools for querying databases with project-based credential management
and connection caching. Currently supports Databricks with extensible architecture
for additional database providers.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from providers.databricks_provider import DatabricksProvider
from providers.snowflake_provider import SnowflakeProvider
from providers.bigquery_provider import BigQueryProvider
from providers.redshift_provider import RedshiftProvider
from providers.glue_provider import GlueProvider
from providers.base_provider import DatabaseProvider
from config import Config
from cache_manager import ConnectionCacheManager
from credential_fetcher import CredentialFetcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("DatabaseServer", host="0.0.0.0", port=8080)

# Global instances
config = Config()
cache_manager = ConnectionCacheManager(
    ttl_seconds=config.CONNECTION_CACHE_TTL,
    max_size=config.CONNECTION_CACHE_MAX_SIZE
)
credential_fetcher = CredentialFetcher(config.API_BASE_URL)

# Provider registry - store classes, not instances
providers: Dict[str, type] = {
    "databricks": DatabricksProvider,
    "snowflake": SnowflakeProvider,
    "bigquery": BigQueryProvider,
    "redshift": RedshiftProvider,
    "glue": GlueProvider
}


async def get_database_client(project_id: str, provider_name: Optional[str] = None) -> DatabaseProvider:
    """
    Get or create a cached database client for the specified project.
    
    Args:
        project_id: Project identifier for credential lookup
        provider_name: Database provider name (optional, auto-detected from credentials)
        
    Returns:
        DatabaseProvider instance
        
    Raises:
        ValueError: If provider is not supported or credentials are invalid
    """
    # Check cache first
    cached_client = cache_manager.get_connection(project_id, provider_name)
    if cached_client:
        logger.info(f"Using cached database client for project: {project_id}")
        return cached_client
    
    # Auto-detect provider type if not specified
    if provider_name is None:
        logger.info(f"Auto-detecting provider type for project: {project_id}")
        # Get all data sources to find the first available provider
        all_data_sources = await credential_fetcher.get_all_data_sources(project_id)
        for ds in all_data_sources:
            ds_type = ds.get("type")
            if ds_type in providers:
                provider_name = ds_type
                logger.info(f"Auto-detected provider type: {provider_name}")
                break
        
        if provider_name is None:
            raise ValueError(f"No supported database provider found for project: {project_id}")
    
    # Fetch credentials for the specified provider type
    logger.info(f"Fetching credentials for project: {project_id}, provider: {provider_name}")
    credentials = await credential_fetcher.get_credentials(project_id, provider_name)
    if not credentials:
        raise ValueError(f"No {provider_name} credentials found for project: {project_id}")
    
    logger.info(f"Retrieved credentials for project {project_id}, type: {credentials.get('type', 'unknown')}")
    
    # Verify the provider type matches what we expected
    actual_provider_type = credentials.get("type")
    if actual_provider_type != provider_name:
        logger.warning(f"Provider type mismatch: expected {provider_name}, got {actual_provider_type}")
        provider_name = actual_provider_type
    
    logger.info(f"Using provider: {provider_name}")
    
    # Get provider
    if provider_name not in providers:
        raise ValueError(f"Unsupported database provider: {provider_name}")
    
    # Create a new instance of the provider for this project
    provider_class = providers[provider_name]
    provider = provider_class()
    
    logger.info(f"Created {provider_name} provider instance, initializing with credentials")
    
    # Initialize provider with credentials
    config_data = credentials.get("configuration", credentials)
    logger.info(f"Initializing provider with config keys: {list(config_data.keys()) if isinstance(config_data, dict) else 'non-dict config'}")
    await provider.initialize(config_data)
    
    # Cache the client
    cache_manager.cache_connection(project_id, provider_name, provider)
    
    logger.info(f"Created and cached new {provider_name} client for project: {project_id}")
    return provider


async def get_supported_providers(project_id: str) -> List[str]:
    """
    Get list of supported database providers for a project.
    
    Args:
        project_id: Project identifier
        
    Returns:
        List of supported provider types
    """
    try:
        # Get all data sources for the project
        all_data_sources = await credential_fetcher.get_all_data_sources(project_id)
        supported_providers = []
        
        for ds in all_data_sources:
            ds_type = ds.get("type")
            if ds_type in providers and ds_type not in supported_providers:
                supported_providers.append(ds_type)
        
        logger.info(f"Found supported providers for project {project_id}: {supported_providers}")
        return supported_providers
        
    except Exception as e:
        logger.error(f"Error getting supported providers for project {project_id}: {e}")
        return []


async def get_provider(project_id: str, provider_type: str) -> Optional[DatabaseProvider]:
    """
    Get a database provider for the specified project and type.
    
    Args:
        project_id: Project identifier for credential lookup
        provider_type: Database provider type (databricks, snowflake)
        
    Returns:
        DatabaseProvider instance or None if error
    """
    try:
        logger.info(f"Getting {provider_type} provider for project {project_id}")
        return await get_database_client(project_id, provider_type)
    except Exception as e:
        logger.error(f"Error getting {provider_type} provider for project {project_id}: {e}", exc_info=True)
        return None


async def _check_provider_support(project_id: str, provider_type: str) -> bool:
    """
    Check if a provider type is supported for the given project.
    
    Args:
        project_id: Project identifier
        provider_type: Provider type to check
        
    Returns:
        True if provider is supported, False otherwise
    """
    supported_providers = await get_supported_providers(project_id)
    return provider_type in supported_providers


async def databricks_query_tool(chicory_project_id: str, catalog: str, schema: str, query: str, limit: int = 100) -> str:
    """
    Execute any SQL query against a Databricks database.
    
    Args:
        chicory_project_id: Project ID for credential lookup
        catalog: Databricks catalog name
        schema: Databricks schema name
        query: SQL query to execute
        limit: Maximum number of rows to return (default: 100)
    
    Returns:
        Query results formatted as a string with row count and data
    """
    try:
        # Check if Databricks is supported for this project
        if not await _check_provider_support(chicory_project_id, "databricks"):
            return "Error: Databricks integration is not configured for this project"
        
        logger.info(f"Executing query for project {chicory_project_id}: {query[:100]}...")
        
        provider = await get_provider(chicory_project_id, "databricks")
        if not provider:
            return "Error: Could not get Databricks provider for project"
        
        result = await provider.execute_query(query, limit=limit, catalog=catalog, schema=schema)
        
        if "error" in result:
            return f"Error executing query: {result['error']}"
        
        rows = result.get('rows', [])
        columns = result.get('columns', [])
        
        # Format result as a readable string
        output = f"Query executed successfully. Rows returned: {len(rows)}\n\n"
        
        if columns:
            output += f"Columns: {', '.join(columns)}\n\n"
        
        if rows:
            output += "Sample data:\n"
            for i, row in enumerate(rows[:10]):  # Show first 10 rows
                output += f"Row {i+1}: {row}\n"
            
            if len(rows) > 10:
                output += f"... and {len(rows) - 10} more rows\n"
        else:
            output += "No data returned.\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in databricks_query_tool: {e}")
        return f"Error: {str(e)}"


async def databricks_list_tables_tool(chicory_project_id: str, catalog: str, schema_name: str) -> str:
    """
    List tables in a Databricks schema using SHOW TABLES.
    
    Args:
        chicory_project_id: Project ID for credential lookup
        catalog: Databricks catalog name
        schema_name: Schema name to list tables from (required)
    
    Returns:
        List of tables formatted as a string
    """
    try:
        # Check if Databricks is supported for this project
        if not await _check_provider_support(chicory_project_id, "databricks"):
            return "Error: Databricks integration is not configured for this project"
        
        logger.info(f"Listing tables for project {chicory_project_id}, schema: {schema_name}")
        
        provider = await get_provider(chicory_project_id, "databricks")
        if not provider:
            return "Error: Could not get Databricks provider for project"
        
        result = await provider.list_tables(catalog, schema_name)
        
        if "error" in result:
            return f"Error listing tables: {result['error']}"
        
        tables = result.get('tables', [])
        schema = result.get('schema', schema_name or 'default')
        
        output = f"Tables in schema '{schema}': {len(tables)} found\n\n"
        
        if tables:
            for table in tables:
                table_name = table.get('name', 'Unknown')
                table_type = table.get('type', 'TABLE')
                output += f"- {table_name} ({table_type})\n"
        else:
            output += "No tables found.\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in databricks_list_tables_tool: {e}")
        return f"Error: {str(e)}"


async def databricks_describe_table_tool(chicory_project_id: str, catalog: str, schema_name: str, table_name: str) -> str:
    """
    Get schema information for a specific table using DESCRIBE.
    
    Args:
        chicory_project_id: Project ID for credential lookup
        catalog: Databricks catalog name
        schema_name: Schema name
        table_name: Table name to describe
    
    Returns:
        Table schema information formatted as a string
    """
    try:
        # Check if Databricks is supported for this project
        if not await _check_provider_support(chicory_project_id, "databricks"):
            return "Error: Databricks integration is not configured for this project"
        
        logger.info(f"Describing table {table_name} for project {chicory_project_id}")
        
        provider = await get_provider(chicory_project_id, "databricks")
        if not provider:
            return "Error: Could not get Databricks provider for project"
        
        result = await provider.describe_table(table_name, catalog, schema_name)
        
        if "error" in result:
            return f"Error describing table: {result['error']}"
        
        columns = result.get('columns', [])
        qualified_name = result.get('table_name', table_name)
        
        output = f"Table Schema: {qualified_name}\n"
        output += f"Columns: {len(columns)}\n\n"
        
        if columns:
            output += "Column Details:\n"
            for col in columns:
                col_name = col.get('name', 'Unknown')
                col_type = col.get('type', 'Unknown')
                col_comment = col.get('comment', '')
                
                output += f"- {col_name}: {col_type}"
                if col_comment:
                    output += f" -- {col_comment}"
                output += "\n"
        else:
            output += "No column information available.\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in databricks_describe_table_tool: {e}")
        return f"Error: {str(e)}"


async def databricks_sample_table_tool(chicory_project_id: str, catalog: str, schema_name: str, table_name: str, limit: int = 10) -> str:
    """
    Sample data from a specific table.
    
    Args:
        chicory_project_id: Project ID for credential lookup
        catalog: Databricks catalog name
        schema_name: Schema name
        table_name: Table name to sample
        limit: Number of sample rows to return (default: 10)
    
    Returns:
        Sample data formatted as a string
    """
    try:
        # Check if Databricks is supported for this project
        if not await _check_provider_support(chicory_project_id, "databricks"):
            return "Error: Databricks integration is not configured for this project"
        
        logger.info(f"Sampling table {table_name} for project {chicory_project_id}, limit: {limit}")
        
        provider = await get_provider(chicory_project_id, "databricks")
        if not provider:
            return "Error: Could not get Databricks provider for project"
        
        result = await provider.sample_table(table_name, catalog, schema_name, limit)
        
        if "error" in result:
            return f"Error sampling table: {result['error']}"
        
        rows = result.get('rows', [])
        columns = result.get('columns', [])
        qualified_name = result.get('table_name', table_name)
        actual_rows = result.get('actual_rows', len(rows))
        
        output = f"Sample Data from: {qualified_name}\n"
        output += f"Requested: {limit} rows, Retrieved: {actual_rows} rows\n\n"
        
        if columns:
            output += f"Columns: {', '.join(columns)}\n\n"
        
        if rows:
            output += "Sample Data:\n"
            for i, row in enumerate(rows):
                output += f"Row {i+1}: {row}\n"
        else:
            output += "No data available.\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in databricks_sample_table_tool: {e}")
        return f"Error: {str(e)}"


# Snowflake Tools
async def snowflake_query_tool(chicory_project_id: str, database: str, schema: str, query: str, limit: int = 100) -> str:
    """
    Execute a SQL query against a Snowflake database.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        database: Snowflake database name
        schema: Snowflake schema name
        query: SQL query to execute
        limit: Maximum number of rows to return (default: 100)
        
    Returns:
        Query results as formatted string
    """
    try:
        # Check if Snowflake is supported for this project
        if not await _check_provider_support(chicory_project_id, "snowflake"):
            return "Error: Snowflake integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "snowflake")
        if not provider:
            return "Error: Could not get Snowflake provider for project"
        
        result = await provider.execute_query(query, limit, database=database, schema=schema)
        
        if "error" in result:
            return f"Query failed: {result['error']}"
        
        # Format output
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        
        if not rows:
            return "Query executed successfully but returned no rows."
        
        # Create formatted output
        output = f"Query: {query}\n"
        output += f"Columns: {', '.join(columns)}\n"
        output += f"Row count: {len(rows)}\n\n"
        
        # Add sample of rows (limit display to prevent overwhelming output)
        display_rows = rows[:10]  # Show max 10 rows in output
        for i, row in enumerate(display_rows):
            if isinstance(row, dict):
                row_str = ", ".join([f"{col}: {row.get(col, 'NULL')}" for col in columns])
            else:
                row_str = ", ".join([str(val) for val in row])
            output += f"Row {i+1}: {row_str}\n"
        
        if len(rows) > 10:
            output += f"... and {len(rows) - 10} more rows\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in snowflake_query_tool: {e}")
        return f"Error: {str(e)}"


async def snowflake_list_tables_tool(chicory_project_id: str, database: str, schema: str) -> str:
    """
    List tables in a Snowflake database and schema.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        database: Database name
        schema: Schema name
        
    Returns:
        List of tables as formatted string
    """
    try:
        # Check if Snowflake is supported for this project
        if not await _check_provider_support(chicory_project_id, "snowflake"):
            return "Error: Snowflake integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "snowflake")
        if not provider:
            return "Error: Could not get Snowflake provider for project"
        
        result = await provider.list_tables(database, schema)
        
        if "error" in result:
            return f"Failed to list tables: {result['error']}"
        
        tables = result.get("tables", [])
        
        if not tables:
            return f"No tables found in {database}.{schema}"
        
        output = f"Tables in {database}.{schema}:\n"
        output += f"Total tables: {len(tables)}\n\n"
        
        for table in tables:
            table_name = table.get("name", "Unknown")
            table_type = table.get("type", "TABLE")
            output += f"- {table_name} ({table_type})\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in snowflake_list_tables_tool: {e}")
        return f"Error: {str(e)}"


async def snowflake_describe_table_tool(chicory_project_id: str, table_name: str, database: Optional[str] = None, schema: Optional[str] = None) -> str:
    """
    Get schema information for a Snowflake table.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        table_name: Name of the table to describe
        database: Database name (optional, uses default if not provided)
        schema: Schema name (optional, uses default if not provided)
        
    Returns:
        Table schema information as formatted string
    """
    try:
        # Check if Snowflake is supported for this project
        if not await _check_provider_support(chicory_project_id, "snowflake"):
            return "Error: Snowflake integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "snowflake")
        if not provider:
            return "Error: Could not get Snowflake provider for project"
        
        result = await provider.describe_table(table_name, database, schema)
        
        if "error" in result:
            return f"Failed to describe table: {result['error']}"
        
        columns = result.get("columns", [])
        
        if not columns:
            return f"No schema information found for table {table_name}"
        
        output = f"Table: {result.get('table_name', table_name)}\n"
        output += f"Database: {result.get('database', 'N/A')}\n"
        output += f"Schema: {result.get('schema', 'N/A')}\n"
        output += f"Columns: {len(columns)}\n\n"
        
        for col in columns:
            col_name = col.get("name", "Unknown")
            col_type = col.get("type", "Unknown")
            nullable = col.get("nullable", "Unknown")
            default = col.get("default", "None")
            primary_key = col.get("primary_key", "No")
            
            output += f"- {col_name}: {col_type}"
            if nullable:
                output += f" (nullable: {nullable})"
            if default and default != "None":
                output += f" (default: {default})"
            if primary_key and primary_key != "No":
                output += f" (primary key: {primary_key})"
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in snowflake_describe_table_tool: {e}")
        return f"Error: {str(e)}"


async def snowflake_sample_table_tool(chicory_project_id: str, table_name: str, database: Optional[str] = None, schema: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Sample data from a Snowflake table.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        table_name: Name of the table to sample
        database: Database name (optional, uses default if not provided)
        schema: Schema name (optional, uses default if not provided)
        limit: Number of rows to sample (default: 10)
        
    Returns:
        Sample data as formatted string
    """
    try:
        # Check if Snowflake is supported for this project
        if not await _check_provider_support(chicory_project_id, "snowflake"):
            return "Error: Snowflake integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "snowflake")
        if not provider:
            return "Error: Could not get Snowflake provider for project"
        
        result = await provider.sample_table(table_name, database, schema, limit)
        
        if "error" in result:
            return f"Failed to sample table: {result['error']}"
        
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        actual_rows = result.get("actual_rows", 0)
        sample_size = result.get("sample_size", limit or 10)
        
        output = f"Table: {result.get('table_name', table_name)}\n"
        output += f"Database: {result.get('database', 'N/A')}\n"
        output += f"Schema: {result.get('schema', 'N/A')}\n"
        output += f"Requested sample size: {sample_size}\n"
        output += f"Actual rows returned: {actual_rows}\n"
        
        if columns:
            output += f"Columns: {', '.join(columns)}\n"
        
        output += "\nSample data:\n"
        
        if not rows:
            output += "No data found in table.\n"
        else:
            for i, row in enumerate(rows):
                if isinstance(row, dict):
                    row_str = ", ".join([f"{col}: {row.get(col, 'NULL')}" for col in columns])
                else:
                    row_str = ", ".join([str(val) for val in row])
                output += f"Row {i+1}: {row_str}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in snowflake_sample_table_tool: {e}")
        return f"Error: {str(e)}"


# BigQuery Tools
async def bigquery_query_tool(chicory_project_id: str, dataset: str, query: str, limit: int = 100) -> str:
    """
    Execute a SQL query against a BigQuery database.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        dataset: BigQuery dataset name
        query: SQL query to execute
        limit: Maximum number of rows to return (default: 100)
        
    Returns:
        Query results as formatted string
    """
    try:
        # Check if BigQuery is supported for this project
        if not await _check_provider_support(chicory_project_id, "bigquery"):
            return "Error: BigQuery integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "bigquery")
        if not provider:
            return "Error: Could not get BigQuery provider for project"
        
        result = await provider.query(query, limit, dataset=dataset)
        
        if "error" in result:
            return f"Query failed: {result['error']}"
        
        # Format output
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        row_count = result.get("row_count", len(rows))
        bytes_processed = result.get("total_bytes_processed", 0)
        
        if not rows:
            return "Query executed successfully but returned no rows."
        
        # Create formatted output
        output = f"Query: {query}\n"
        output += f"Columns: {', '.join([col['name'] for col in columns])}\n"
        output += f"Row count: {row_count}\n"
        output += f"Bytes processed: {bytes_processed:,}\n\n"
        
        # Add sample of rows (limit display to prevent overwhelming output)
        display_rows = rows[:10]  # Show max 10 rows in output
        for i, row in enumerate(display_rows):
            if isinstance(row, dict):
                row_str = ", ".join([f"{col['name']}: {row.get(col['name'], 'NULL')}" for col in columns])
            else:
                row_str = ", ".join([str(val) for val in row])
            output += f"Row {i+1}: {row_str}\n"
        
        if len(rows) > 10:
            output += f"... and {len(rows) - 10} more rows\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in bigquery_query_tool: {e}")
        return f"Error: {str(e)}"


async def bigquery_list_tables_tool(chicory_project_id: str, dataset: Optional[str] = None) -> str:
    """
    List tables in BigQuery datasets.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        dataset: Dataset name (optional, lists from all datasets if not provided)
        
    Returns:
        List of tables as formatted string
    """
    try:
        # Check if BigQuery is supported for this project
        if not await _check_provider_support(chicory_project_id, "bigquery"):
            return "Error: BigQuery integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "bigquery")
        if not provider:
            return "Error: Could not get BigQuery provider for project"
        
        result = await provider.list_tables(dataset)
        
        if not result:
            return f"No tables found in dataset {dataset}" if dataset else "No tables found"
        
        output = f"Tables in {'dataset ' + dataset if dataset else 'all datasets'}:\n"
        output += f"Total tables: {len(result)}\n\n"
        
        for table in result:
            table_name = table.get("table_id", "Unknown")
            dataset_id = table.get("dataset_id", "Unknown") 
            table_type = table.get("table_type", "TABLE")
            num_rows = table.get("num_rows", "Unknown")
            created = table.get("created", "Unknown")
            
            output += f"- {dataset_id}.{table_name} ({table_type})"
            if num_rows is not None and num_rows != "Unknown":
                output += f" - {num_rows:,} rows"
            if created != "Unknown" and created is not None:
                output += f" - created: {created[:10]}"  # Just date part
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in bigquery_list_tables_tool: {e}")
        return f"Error: {str(e)}"


async def bigquery_describe_table_tool(chicory_project_id: str, table_id: str, dataset: Optional[str] = None) -> str:
    """
    Get schema information for a BigQuery table.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        table_id: Table identifier (can be full path project.dataset.table or just table name)
        dataset: Dataset name (optional if table_id is fully qualified)
        
    Returns:
        Table schema information as formatted string
    """
    try:
        # Check if BigQuery is supported for this project
        if not await _check_provider_support(chicory_project_id, "bigquery"):
            return "Error: BigQuery integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "bigquery")
        if not provider:
            return "Error: Could not get BigQuery provider for project"
        
        result = await provider.describe_table(table_id, dataset)
        
        full_table_id = result.get("full_table_id", table_id)
        schema = result.get("schema", [])
        num_rows = result.get("num_rows", "Unknown")
        num_bytes = result.get("num_bytes", "Unknown")
        created = result.get("created", "Unknown")
        modified = result.get("modified", "Unknown")
        description = result.get("description", "")
        
        output = f"Table: {full_table_id}\n"
        if description:
            output += f"Description: {description}\n"
        output += f"Rows: {num_rows:,}\n" if num_rows != "Unknown" else "Rows: Unknown\n"
        output += f"Size: {num_bytes:,} bytes\n" if num_bytes != "Unknown" else "Size: Unknown\n"
        output += f"Created: {created[:19] if created != 'Unknown' else 'Unknown'}\n"
        output += f"Modified: {modified[:19] if modified != 'Unknown' else 'Unknown'}\n"
        output += f"Columns: {len(schema)}\n\n"
        
        if schema:
            output += "Schema:\n"
            for field in schema:
                field_name = field.get("name", "Unknown")
                field_type = field.get("field_type", "Unknown")
                mode = field.get("mode", "NULLABLE")
                field_desc = field.get("description", "")
                
                output += f"- {field_name}: {field_type} ({mode})"
                if field_desc:
                    output += f" -- {field_desc}"
                output += "\n"
        else:
            output += "No schema information available.\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in bigquery_describe_table_tool: {e}")
        return f"Error: {str(e)}"


async def bigquery_sample_table_tool(chicory_project_id: str, table_id: str, dataset: Optional[str] = None, limit: int = 10) -> str:
    """
    Sample data from a BigQuery table.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        table_id: Table identifier (can be full path project.dataset.table or just table name)
        dataset: Dataset name (optional if table_id is fully qualified)
        limit: Number of rows to sample (default: 10)
        
    Returns:
        Sample data as formatted string
    """
    try:
        # Check if BigQuery is supported for this project
        if not await _check_provider_support(chicory_project_id, "bigquery"):
            return "Error: BigQuery integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "bigquery")
        if not provider:
            return "Error: Could not get BigQuery provider for project"
        
        result = await provider.sample_table(table_id, dataset, limit)
        
        full_table_id = result.get("table_id", table_id)
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        sample_size = result.get("sample_size", 0)
        bytes_processed = result.get("total_bytes_processed", 0)
        
        output = f"Table: {full_table_id}\n"
        output += f"Requested sample size: {limit}\n"
        output += f"Actual rows returned: {sample_size}\n"
        output += f"Bytes processed: {bytes_processed:,}\n"
        
        if columns:
            output += f"Columns: {', '.join([col['name'] for col in columns])}\n"
        
        output += "\nSample data:\n"
        
        if not rows:
            output += "No data found in table.\n"
        else:
            for i, row in enumerate(rows):
                if isinstance(row, dict):
                    row_str = ", ".join([f"{col['name']}: {row.get(col['name'], 'NULL')}" for col in columns])
                else:
                    row_str = ", ".join([str(val) for val in row])
                output += f"Row {i+1}: {row_str}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in bigquery_sample_table_tool: {e}")
        return f"Error: {str(e)}"


# Redshift Tools
async def redshift_query_tool(chicory_project_id: str, query: str, limit: int = 100) -> str:
    """
    Execute a SQL query against a Redshift database.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        query: SQL query to execute
        limit: Maximum number of rows to return (default: 100)
        
    Returns:
        Query results as formatted string
    """
    try:
        # Check if Redshift is supported for this project
        if not await _check_provider_support(chicory_project_id, "redshift"):
            return "Error: Redshift integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "redshift")
        if not provider:
            return "Error: Could not get Redshift provider for project"
        
        result = await provider.execute_query(query, limit)
        
        if "error" in result:
            return f"Query failed: {result['error']}"
        
        # Format output
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        row_count = result.get("row_count", len(rows))
        
        if not rows:
            return "Query executed successfully but returned no rows."
        
        # Create formatted output
        output = f"Query: {query}\n"
        output += f"Columns: {', '.join(columns)}\n"
        output += f"Row count: {row_count}\n\n"
        
        # Add sample of rows (limit display to prevent overwhelming output)
        display_rows = rows[:10]  # Show max 10 rows in output
        for i, row in enumerate(display_rows):
            if isinstance(row, dict):
                row_str = ", ".join([f"{col}: {row.get(col, 'NULL')}" for col in columns])
            else:
                row_str = ", ".join([str(val) for val in row])
            output += f"Row {i+1}: {row_str}\n"
        
        if len(rows) > 10:
            output += f"... and {len(rows) - 10} more rows\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redshift_query_tool: {e}")
        return f"Error: {str(e)}"


async def redshift_list_tables_tool(chicory_project_id: str, schema: Optional[str] = None) -> str:
    """
    List tables in Redshift schemas.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        schema: Schema name (optional, lists from public schema if not provided)
        
    Returns:
        List of tables as formatted string
    """
    try:
        # Check if Redshift is supported for this project
        if not await _check_provider_support(chicory_project_id, "redshift"):
            return "Error: Redshift integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "redshift")
        if not provider:
            return "Error: Could not get Redshift provider for project"
        
        result = await provider.list_tables(schema)
        
        if "error" in result:
            return f"Failed to list tables: {result['error']}"
        
        tables = result.get("tables", [])
        schema_name = result.get("schema", schema or "public")
        
        if not tables:
            return f"No tables found in schema {schema_name}"
        
        output = f"Tables in schema {schema_name}:\n"
        output += f"Total tables: {len(tables)}\n\n"
        
        for table in tables:
            table_name = table.get("name", "Unknown")
            table_type = table.get("type", "TABLE")
            owner = table.get("owner", "Unknown")
            output += f"- {table_name} ({table_type}) - Owner: {owner}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redshift_list_tables_tool: {e}")
        return f"Error: {str(e)}"


async def redshift_describe_table_tool(chicory_project_id: str, table_name: str, schema: Optional[str] = None) -> str:
    """
    Get schema information for a Redshift table.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        table_name: Name of the table to describe
        schema: Schema name (optional, uses public if not provided)
        
    Returns:
        Table schema information as formatted string
    """
    try:
        # Check if Redshift is supported for this project
        if not await _check_provider_support(chicory_project_id, "redshift"):
            return "Error: Redshift integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "redshift")
        if not provider:
            return "Error: Could not get Redshift provider for project"
        
        result = await provider.describe_table(table_name, schema)
        
        if "error" in result:
            return f"Failed to describe table: {result['error']}"
        
        columns = result.get("columns", [])
        table_name_full = result.get("table_name", table_name)
        
        if not columns:
            return f"No schema information found for table {table_name_full}"
        
        output = f"Table: {table_name_full}\n"
        output += f"Schema: {result.get('schema', 'public')}\n"
        output += f"Columns: {len(columns)}\n\n"
        
        for col in columns:
            col_name = col.get("name", "Unknown")
            col_type = col.get("type", "Unknown")
            nullable = col.get("nullable", True)
            default = col.get("default")
            position = col.get("position", "")
            
            output += f"- {col_name}: {col_type}"
            if not nullable:
                output += " NOT NULL"
            if default:
                output += f" DEFAULT {default}"
            if position:
                output += f" (pos: {position})"
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redshift_describe_table_tool: {e}")
        return f"Error: {str(e)}"


async def redshift_sample_table_tool(chicory_project_id: str, table_name: str, schema: Optional[str] = None, limit: int = 10) -> str:
    """
    Sample data from a Redshift table.
    
    Args:
        chicory_project_id: Project identifier for credential lookup
        table_name: Name of the table to sample
        schema: Schema name (optional, uses public if not provided)
        limit: Number of rows to sample (default: 10)
        
    Returns:
        Sample data as formatted string
    """
    try:
        # Check if Redshift is supported for this project
        if not await _check_provider_support(chicory_project_id, "redshift"):
            return "Error: Redshift integration is not configured for this project"
        
        provider = await get_provider(chicory_project_id, "redshift")
        if not provider:
            return "Error: Could not get Redshift provider for project"
        
        result = await provider.sample_table(table_name, schema, limit)
        
        if "error" in result:
            return f"Failed to sample table: {result['error']}"
        
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        actual_rows = result.get("actual_rows", 0)
        sample_size = result.get("sample_size", limit)
        table_name_full = result.get("table_name", table_name)
        
        output = f"Table: {table_name_full}\n"
        output += f"Schema: {result.get('schema', 'public')}\n"
        output += f"Requested sample size: {limit}\n"
        output += f"Actual rows returned: {actual_rows}\n"
        
        if columns:
            output += f"Columns: {', '.join(columns)}\n"
        
        output += "\nSample data:\n"
        
        if not rows:
            output += "No data found in table.\n"
        else:
            for i, row in enumerate(rows):
                if isinstance(row, dict):
                    row_str = ", ".join([f"{col}: {row.get(col, 'NULL')}" for col in columns])
                else:
                    row_str = ", ".join([str(val) for val in row])
                output += f"Row {i+1}: {row_str}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redshift_sample_table_tool: {e}")
        return f"Error: {str(e)}"


# Glue Tools
async def glue_list_databases_tool(chicory_project_id: str) -> str:
    """
    List all databases in AWS Glue Data Catalog.

    Args:
        chicory_project_id: Project identifier for credential lookup

    Returns:
        List of databases as formatted string
    """
    try:
        # Check if Glue is supported for this project
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.list_databases()

        if "error" in result:
            return f"Failed to list databases: {result['error']}"

        databases = result.get("databases", [])

        if not databases:
            return "No databases found in Glue Data Catalog"

        output = f"Databases in Glue Data Catalog:\n"
        output += f"Total databases: {len(databases)}\n\n"

        for db in databases:
            db_name = db.get("name", "Unknown")
            description = db.get("description", "")
            location = db.get("location_uri", "")

            output += f"- {db_name}"
            if description:
                output += f" - {description}"
            if location:
                output += f"\n  Location: {location}"
            output += "\n"

        return output

    except Exception as e:
        logger.error(f"Error in glue_list_databases_tool: {e}")
        return f"Error: {str(e)}"


async def glue_list_tables_tool(chicory_project_id: str, database_name: str) -> str:
    """
    List tables in an AWS Glue database.

    Args:
        chicory_project_id: Project identifier for credential lookup
        database_name: Database name in Glue Data Catalog

    Returns:
        List of tables as formatted string
    """
    try:
        # Check if Glue is supported for this project
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.list_tables(database_name)

        if "error" in result:
            return f"Failed to list tables: {result['error']}"

        tables = result.get("tables", [])

        if not tables:
            return f"No tables found in database {database_name}"

        output = f"Tables in database {database_name}:\n"
        output += f"Total tables: {len(tables)}\n\n"

        for table in tables:
            table_name = table.get("name", "Unknown")
            table_type = table.get("table_type", "")
            location = table.get("storage_descriptor", {}).get("location", "")
            partition_keys = table.get("partition_keys", [])

            output += f"- {table_name}"
            if table_type:
                output += f" ({table_type})"
            if partition_keys:
                output += f" - Partitioned by: {', '.join([pk['name'] for pk in partition_keys])}"
            if location:
                output += f"\n  Location: {location}"
            output += "\n"

        return output

    except Exception as e:
        logger.error(f"Error in glue_list_tables_tool: {e}")
        return f"Error: {str(e)}"


async def glue_describe_table_tool(chicory_project_id: str, database_name: str, table_name: str) -> str:
    """
    Get schema information for an AWS Glue table.

    Args:
        chicory_project_id: Project identifier for credential lookup
        database_name: Database name in Glue Data Catalog
        table_name: Table name to describe

    Returns:
        Table schema information as formatted string
    """
    try:
        # Check if Glue is supported for this project
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.describe_table(database_name, table_name)

        if "error" in result:
            return f"Failed to describe table: {result['error']}"

        columns = result.get("columns", [])
        partition_keys = result.get("partition_keys", [])
        storage_desc = result.get("storage_descriptor", {})

        if not columns:
            return f"No schema information found for table {database_name}.{table_name}"

        output = f"Table: {result.get('table_name', table_name)}\n"
        output += f"Database: {result.get('database', database_name)}\n"

        if result.get("description"):
            output += f"Description: {result.get('description')}\n"

        output += f"Table Type: {result.get('table_type', 'N/A')}\n"
        output += f"Location: {storage_desc.get('location', 'N/A')}\n"
        output += f"Input Format: {storage_desc.get('input_format', 'N/A')}\n"
        output += f"Output Format: {storage_desc.get('output_format', 'N/A')}\n"

        if result.get("create_time"):
            output += f"Created: {result.get('create_time')}\n"
        if result.get("update_time"):
            output += f"Updated: {result.get('update_time')}\n"

        output += f"\nColumns: {len(columns)}\n"
        for col in columns:
            col_name = col.get("name", "Unknown")
            col_type = col.get("type", "Unknown")
            col_comment = col.get("comment", "")

            output += f"- {col_name}: {col_type}"
            if col_comment:
                output += f" -- {col_comment}"
            output += "\n"

        if partition_keys:
            output += f"\nPartition Keys: {len(partition_keys)}\n"
            for pk in partition_keys:
                pk_name = pk.get("name", "Unknown")
                pk_type = pk.get("type", "Unknown")
                pk_comment = pk.get("comment", "")

                output += f"- {pk_name}: {pk_type}"
                if pk_comment:
                    output += f" -- {pk_comment}"
                output += "\n"

        return output

    except Exception as e:
        logger.error(f"Error in glue_describe_table_tool: {e}")
        return f"Error: {str(e)}"


async def glue_get_partitions_tool(chicory_project_id: str, database_name: str, table_name: str, max_results: int = 100) -> str:
    """
    Get partitions for an AWS Glue table.

    Args:
        chicory_project_id: Project identifier for credential lookup
        database_name: Database name in Glue Data Catalog
        table_name: Table name
        max_results: Maximum number of partitions to return (default: 100)

    Returns:
        Partition information as formatted string
    """
    try:
        # Check if Glue is supported for this project
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.get_partitions(database_name, table_name, max_results)

        if "error" in result:
            return f"Failed to get partitions: {result['error']}"

        partitions = result.get("partitions", [])

        if not partitions:
            return f"No partitions found for table {database_name}.{table_name}"

        output = f"Partitions for {database_name}.{table_name}:\n"
        output += f"Total partitions: {len(partitions)}\n"
        output += f"Showing: {min(len(partitions), max_results)}\n\n"

        for i, partition in enumerate(partitions[:10], 1):  # Show first 10
            values = partition.get("values", [])
            location = partition.get("storage_descriptor", {}).get("location", "")
            create_time = partition.get("create_time", "")

            output += f"Partition {i}: {values}"
            if location:
                output += f"\n  Location: {location}"
            if create_time:
                output += f"\n  Created: {create_time}"
            output += "\n"

        if len(partitions) > 10:
            output += f"\n... and {len(partitions) - 10} more partitions\n"

        return output

    except Exception as e:
        logger.error(f"Error in glue_get_partitions_tool: {e}")
        return f"Error: {str(e)}"


# Glue Data Quality Ruleset Tools
async def glue_create_data_quality_ruleset_tool(
    chicory_project_id: str,
    name: str,
    ruleset: str,
    database_name: str,
    table_name: str,
    description: Optional[str] = None
) -> str:
    """Create a data quality ruleset for an AWS Glue table."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.create_data_quality_ruleset(
            name=name,
            ruleset=ruleset,
            database_name=database_name,
            table_name=table_name,
            description=description
        )

        if "error" in result:
            return f"Failed to create ruleset: {result['error']}"

        return f"Successfully created data quality ruleset: {result.get('name')}"

    except Exception as e:
        logger.error(f"Error in glue_create_data_quality_ruleset_tool: {e}")
        return f"Error: {str(e)}"


async def glue_get_data_quality_ruleset_tool(chicory_project_id: str, name: str) -> str:
    """Get a data quality ruleset by name."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.get_data_quality_ruleset(name)

        if "error" in result:
            return f"Failed to get ruleset: {result['error']}"

        output = f"Data Quality Ruleset: {result.get('name')}\n"
        output += f"Description: {result.get('description', 'N/A')}\n"
        output += f"Created: {result.get('created_on', 'N/A')}\n"
        output += f"Last Modified: {result.get('last_modified_on', 'N/A')}\n"
        output += f"Target Table: {result.get('target_table', {})}\n"
        output += f"\nRuleset:\n{result.get('ruleset', '')}"

        return output

    except Exception as e:
        logger.error(f"Error in glue_get_data_quality_ruleset_tool: {e}")
        return f"Error: {str(e)}"


async def glue_update_data_quality_ruleset_tool(
    chicory_project_id: str,
    name: str,
    ruleset: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """Update a data quality ruleset."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.update_data_quality_ruleset(name, ruleset, description)

        if "error" in result:
            return f"Failed to update ruleset: {result['error']}"

        return f"Successfully updated data quality ruleset: {result.get('name')}"

    except Exception as e:
        logger.error(f"Error in glue_update_data_quality_ruleset_tool: {e}")
        return f"Error: {str(e)}"


async def glue_delete_data_quality_ruleset_tool(chicory_project_id: str, name: str) -> str:
    """Delete a data quality ruleset."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.delete_data_quality_ruleset(name)

        if "error" in result:
            return f"Failed to delete ruleset: {result['error']}"

        return f"Successfully deleted data quality ruleset: {name}"

    except Exception as e:
        logger.error(f"Error in glue_delete_data_quality_ruleset_tool: {e}")
        return f"Error: {str(e)}"


async def glue_list_data_quality_rulesets_tool(
    chicory_project_id: str,
    database_name: Optional[str] = None,
    table_name: Optional[str] = None,
    max_results: int = 100
) -> str:
    """List data quality rulesets."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.list_data_quality_rulesets(database_name, table_name, max_results)

        if "error" in result:
            return f"Failed to list rulesets: {result['error']}"

        rulesets = result.get("rulesets", [])
        output = f"Data Quality Rulesets: {len(rulesets)}\n\n"

        for ruleset in rulesets:
            output += f"- {ruleset.get('name')}\n"
            if ruleset.get('description'):
                output += f"  Description: {ruleset.get('description')}\n"
            output += f"  Target: {ruleset.get('target_table', {})}\n"
            output += f"  Created: {ruleset.get('created_on', 'N/A')}\n\n"

        return output if rulesets else "No data quality rulesets found"

    except Exception as e:
        logger.error(f"Error in glue_list_data_quality_rulesets_tool: {e}")
        return f"Error: {str(e)}"


async def glue_start_data_quality_rule_recommendation_run_tool(
    chicory_project_id: str,
    database_name: str,
    table_name: str,
    role: str,
    number_of_workers: int = 5
) -> str:
    """Start a data quality rule recommendation run."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.start_data_quality_rule_recommendation_run(
            database_name, table_name, role, number_of_workers
        )

        if "error" in result:
            return f"Failed to start recommendation run: {result['error']}"

        return f"Successfully started recommendation run. Run ID: {result.get('run_id')}"

    except Exception as e:
        logger.error(f"Error in glue_start_data_quality_rule_recommendation_run_tool: {e}")
        return f"Error: {str(e)}"


async def glue_get_data_quality_rule_recommendation_run_tool(chicory_project_id: str, run_id: str) -> str:
    """Get status of a data quality rule recommendation run."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.get_data_quality_rule_recommendation_run(run_id)

        if "error" in result:
            return f"Failed to get recommendation run: {result['error']}"

        output = f"Recommendation Run ID: {result.get('run_id')}\n"
        output += f"Status: {result.get('status')}\n"
        output += f"Started: {result.get('started_on', 'N/A')}\n"
        output += f"Completed: {result.get('completed_on', 'N/A')}\n"
        output += f"Execution Time: {result.get('execution_time', 'N/A')} seconds\n"
        output += f"\nRecommended Ruleset:\n{result.get('recommended_ruleset', 'N/A')}"

        return output

    except Exception as e:
        logger.error(f"Error in glue_get_data_quality_rule_recommendation_run_tool: {e}")
        return f"Error: {str(e)}"


async def glue_start_data_quality_ruleset_evaluation_run_tool(
    chicory_project_id: str,
    database_name: str,
    table_name: str,
    ruleset_names: str,
    role: str,
    number_of_workers: int = 5
) -> str:
    """Start a data quality ruleset evaluation run."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        # Parse comma-separated ruleset names
        rulesets = [name.strip() for name in ruleset_names.split(",")]

        result = await provider.start_data_quality_ruleset_evaluation_run(
            database_name, table_name, rulesets, role, number_of_workers
        )

        if "error" in result:
            return f"Failed to start evaluation run: {result['error']}"

        return f"Successfully started evaluation run. Run ID: {result.get('run_id')}"

    except Exception as e:
        logger.error(f"Error in glue_start_data_quality_ruleset_evaluation_run_tool: {e}")
        return f"Error: {str(e)}"


async def glue_get_data_quality_ruleset_evaluation_run_tool(chicory_project_id: str, run_id: str) -> str:
    """Get status of a data quality ruleset evaluation run."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.get_data_quality_ruleset_evaluation_run(run_id)

        if "error" in result:
            return f"Failed to get evaluation run: {result['error']}"

        output = f"Evaluation Run ID: {result.get('run_id')}\n"
        output += f"Status: {result.get('status')}\n"
        output += f"Started: {result.get('started_on', 'N/A')}\n"
        output += f"Completed: {result.get('completed_on', 'N/A')}\n"
        output += f"Execution Time: {result.get('execution_time', 'N/A')} seconds\n"
        output += f"Rulesets: {', '.join(result.get('ruleset_names', []))}\n"
        output += f"Result IDs: {', '.join(result.get('result_ids', []))}"

        return output

    except Exception as e:
        logger.error(f"Error in glue_get_data_quality_ruleset_evaluation_run_tool: {e}")
        return f"Error: {str(e)}"


async def glue_list_data_quality_results_tool(
    chicory_project_id: str,
    database_name: Optional[str] = None,
    table_name: Optional[str] = None,
    max_results: int = 100
) -> str:
    """List data quality results."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.list_data_quality_results(database_name, table_name, max_results)

        if "error" in result:
            return f"Failed to list results: {result['error']}"

        results = result.get("results", [])
        output = f"Data Quality Results: {len(results)}\n\n"

        for res in results:
            output += f"Result ID: {res.get('result_id')}\n"
            output += f"  Score: {res.get('score', 'N/A')}\n"
            output += f"  Job: {res.get('job_name', 'N/A')}\n"
            output += f"  Ruleset: {res.get('ruleset_name', 'N/A')}\n"
            output += f"  Started: {res.get('started_on', 'N/A')}\n"
            output += f"  Completed: {res.get('completed_on', 'N/A')}\n\n"

        return output if results else "No data quality results found"

    except Exception as e:
        logger.error(f"Error in glue_list_data_quality_results_tool: {e}")
        return f"Error: {str(e)}"


# Glue Column Statistics Tools
async def glue_get_column_statistics_for_table_tool(
    chicory_project_id: str,
    database_name: str,
    table_name: str,
    column_names: str
) -> str:
    """Get column statistics for a table."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        columns = [col.strip() for col in column_names.split(",")]
        result = await provider.get_column_statistics_for_table(database_name, table_name, columns)

        if "error" in result:
            return f"Failed to get column statistics: {result['error']}"

        stats = result.get("column_statistics", [])
        output = f"Column Statistics for {database_name}.{table_name}:\n\n"

        for stat in stats:
            output += f"Column: {stat.get('column_name')} ({stat.get('column_type')})\n"
            output += f"  Analyzed: {stat.get('analyzed_time', 'N/A')}\n"
            stats_data = stat.get('statistics_data', {})
            if stats_data:
                output += "  Statistics:\n"
                for key, value in stats_data.items():
                    output += f"    {key}: {value}\n"
            output += "\n"

        return output if stats else "No column statistics found"

    except Exception as e:
        logger.error(f"Error in glue_get_column_statistics_for_table_tool: {e}")
        return f"Error: {str(e)}"


async def glue_get_column_statistics_for_partition_tool(
    chicory_project_id: str,
    database_name: str,
    table_name: str,
    partition_values: str,
    column_names: str
) -> str:
    """Get column statistics for a partition."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        partitions = [val.strip() for val in partition_values.split(",")]
        columns = [col.strip() for col in column_names.split(",")]

        result = await provider.get_column_statistics_for_partition(
            database_name, table_name, partitions, columns
        )

        if "error" in result:
            return f"Failed to get column statistics: {result['error']}"

        stats = result.get("column_statistics", [])
        output = f"Column Statistics for {database_name}.{table_name} (Partition: {partitions}):\n\n"

        for stat in stats:
            output += f"Column: {stat.get('column_name')} ({stat.get('column_type')})\n"
            output += f"  Analyzed: {stat.get('analyzed_time', 'N/A')}\n"
            stats_data = stat.get('statistics_data', {})
            if stats_data:
                output += "  Statistics:\n"
                for key, value in stats_data.items():
                    output += f"    {key}: {value}\n"
            output += "\n"

        return output if stats else "No column statistics found"

    except Exception as e:
        logger.error(f"Error in glue_get_column_statistics_for_partition_tool: {e}")
        return f"Error: {str(e)}"


async def glue_delete_column_statistics_for_table_tool(
    chicory_project_id: str,
    database_name: str,
    table_name: str,
    column_name: str
) -> str:
    """Delete column statistics for a table column."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.delete_column_statistics_for_table(database_name, table_name, column_name)

        if "error" in result:
            return f"Failed to delete column statistics: {result['error']}"

        return f"Successfully deleted column statistics for {database_name}.{table_name}.{column_name}"

    except Exception as e:
        logger.error(f"Error in glue_delete_column_statistics_for_table_tool: {e}")
        return f"Error: {str(e)}"


async def glue_delete_column_statistics_for_partition_tool(
    chicory_project_id: str,
    database_name: str,
    table_name: str,
    partition_values: str,
    column_name: str
) -> str:
    """Delete column statistics for a partition column."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        partitions = [val.strip() for val in partition_values.split(",")]

        result = await provider.delete_column_statistics_for_partition(
            database_name, table_name, partitions, column_name
        )

        if "error" in result:
            return f"Failed to delete column statistics: {result['error']}"

        return f"Successfully deleted column statistics for {database_name}.{table_name}.{column_name} (Partition: {partitions})"

    except Exception as e:
        logger.error(f"Error in glue_delete_column_statistics_for_partition_tool: {e}")
        return f"Error: {str(e)}"


# Athena Tools (via Glue provider)
async def glue_athena_create_work_group_tool(
    chicory_project_id: str,
    name: str,
    description: Optional[str] = None
) -> str:
    """Create an Athena workgroup."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_create_work_group(name, description)

        if "error" in result:
            return f"Failed to create workgroup: {result['error']}"

        return f"Successfully created Athena workgroup: {result.get('name')}"

    except Exception as e:
        logger.error(f"Error in glue_athena_create_work_group_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_list_work_groups_tool(
    chicory_project_id: str,
    max_results: int = 50
) -> str:
    """List Athena workgroups."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_list_work_groups(max_results)

        if "error" in result:
            return f"Failed to list workgroups: {result['error']}"

        workgroups = result.get("workgroups", [])
        output = f"Athena Workgroups: {len(workgroups)}\n\n"

        for wg in workgroups:
            output += f"Name: {wg.get('name')}\n"
            output += f"  State: {wg.get('state')}\n"
            output += f"  Description: {wg.get('description', 'N/A')}\n"
            output += f"  Created: {wg.get('creation_time', 'N/A')}\n\n"

        return output if workgroups else "No workgroups found"

    except Exception as e:
        logger.error(f"Error in glue_athena_list_work_groups_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_get_work_group_tool(chicory_project_id: str, name: str) -> str:
    """Get details of an Athena workgroup."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_get_work_group(name)

        if "error" in result:
            return f"Failed to get workgroup: {result['error']}"

        output = f"Workgroup: {result.get('name')}\n"
        output += f"State: {result.get('state')}\n"
        output += f"Description: {result.get('description', 'N/A')}\n"
        output += f"Created: {result.get('creation_time', 'N/A')}\n"
        output += f"Configuration: {result.get('configuration', {})}"

        return output

    except Exception as e:
        logger.error(f"Error in glue_athena_get_work_group_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_update_work_group_tool(
    chicory_project_id: str,
    name: str,
    description: Optional[str] = None,
    state: Optional[str] = None
) -> str:
    """Update an Athena workgroup."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_update_work_group(name, description, None, state)

        if "error" in result:
            return f"Failed to update workgroup: {result['error']}"

        return f"Successfully updated Athena workgroup: {result.get('name')}"

    except Exception as e:
        logger.error(f"Error in glue_athena_update_work_group_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_delete_work_group_tool(
    chicory_project_id: str,
    name: str,
    recursive_delete: bool = False
) -> str:
    """Delete an Athena workgroup."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_delete_work_group(name, recursive_delete)

        if "error" in result:
            return f"Failed to delete workgroup: {result['error']}"

        return f"Successfully deleted Athena workgroup: {result.get('name')}"

    except Exception as e:
        logger.error(f"Error in glue_athena_delete_work_group_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_get_data_catalog_tool(chicory_project_id: str, name: str) -> str:
    """Get details of an Athena data catalog."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_get_data_catalog(name)

        if "error" in result:
            return f"Failed to get data catalog: {result['error']}"

        output = f"Data Catalog: {result.get('name')}\n"
        output += f"Type: {result.get('type')}\n"
        output += f"Description: {result.get('description', 'N/A')}\n"
        output += f"Parameters: {result.get('parameters', {})}"

        return output

    except Exception as e:
        logger.error(f"Error in glue_athena_get_data_catalog_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_list_data_catalogs_tool(
    chicory_project_id: str,
    max_results: int = 50
) -> str:
    """List Athena data catalogs."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_list_data_catalogs(max_results)

        if "error" in result:
            return f"Failed to list data catalogs: {result['error']}"

        catalogs = result.get("catalogs", [])
        output = f"Athena Data Catalogs: {len(catalogs)}\n\n"

        for catalog in catalogs:
            output += f"Name: {catalog.get('catalog_name')}\n"
            output += f"  Type: {catalog.get('type')}\n\n"

        return output if catalogs else "No data catalogs found"

    except Exception as e:
        logger.error(f"Error in glue_athena_list_data_catalogs_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_update_data_catalog_tool(
    chicory_project_id: str,
    name: str,
    type: str,
    description: Optional[str] = None
) -> str:
    """Update an Athena data catalog."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_update_data_catalog(name, type, description)

        if "error" in result:
            return f"Failed to update data catalog: {result['error']}"

        return f"Successfully updated Athena data catalog: {result.get('name')}"

    except Exception as e:
        logger.error(f"Error in glue_athena_update_data_catalog_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_start_query_execution_tool(
    chicory_project_id: str,
    query_string: str,
    database: Optional[str] = None,
    output_location: Optional[str] = None,
    work_group: Optional[str] = None
) -> str:
    """Start an Athena query execution."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_start_query_execution(
            query_string, database, output_location, work_group
        )

        if "error" in result:
            return f"Failed to start query execution: {result['error']}"

        return f"Successfully started query execution. Query Execution ID: {result.get('query_execution_id')}"

    except Exception as e:
        logger.error(f"Error in glue_athena_start_query_execution_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_get_query_execution_tool(
    chicory_project_id: str,
    query_execution_id: str
) -> str:
    """Get details of an Athena query execution."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_get_query_execution(query_execution_id)

        if "error" in result:
            return f"Failed to get query execution: {result['error']}"

        output = f"Query Execution ID: {result.get('query_execution_id')}\n"
        output += f"State: {result.get('state')}\n"
        output += f"Query: {result.get('query')}\n"
        output += f"Workgroup: {result.get('work_group', 'N/A')}\n"
        output += f"Submitted: {result.get('submission_date_time', 'N/A')}\n"
        output += f"Completed: {result.get('completion_date_time', 'N/A')}\n"
        output += f"State Change Reason: {result.get('state_change_reason', 'N/A')}\n"
        output += f"Statistics: {result.get('statistics', {})}"

        return output

    except Exception as e:
        logger.error(f"Error in glue_athena_get_query_execution_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_stop_query_execution_tool(
    chicory_project_id: str,
    query_execution_id: str
) -> str:
    """Stop an Athena query execution."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_stop_query_execution(query_execution_id)

        if "error" in result:
            return f"Failed to stop query execution: {result['error']}"

        return f"Successfully stopped query execution: {result.get('query_execution_id')}"

    except Exception as e:
        logger.error(f"Error in glue_athena_stop_query_execution_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_get_query_results_tool(
    chicory_project_id: str,
    query_execution_id: str,
    max_results: int = 1000
) -> str:
    """Get results of an Athena query execution."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_get_query_results(query_execution_id, max_results)

        if "error" in result:
            return f"Failed to get query results: {result['error']}"

        rows = result.get("rows", [])
        output = f"Query Results: {len(rows)} rows\n\n"

        if rows:
            # Display first 10 rows
            for i, row in enumerate(rows[:10]):
                output += f"Row {i+1}: {row}\n"

            if len(rows) > 10:
                output += f"\n... and {len(rows) - 10} more rows"

        return output if rows else "No results found"

    except Exception as e:
        logger.error(f"Error in glue_athena_get_query_results_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_list_query_executions_tool(
    chicory_project_id: str,
    work_group: Optional[str] = None,
    max_results: int = 50
) -> str:
    """List Athena query executions."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        result = await provider.athena_list_query_executions(work_group, max_results)

        if "error" in result:
            return f"Failed to list query executions: {result['error']}"

        query_execution_ids = result.get("query_execution_ids", [])
        output = f"Query Execution IDs: {len(query_execution_ids)}\n\n"

        for qe_id in query_execution_ids[:20]:
            output += f"  {qe_id}\n"

        if len(query_execution_ids) > 20:
            output += f"\n... and {len(query_execution_ids) - 20} more"

        return output if query_execution_ids else "No query executions found"

    except Exception as e:
        logger.error(f"Error in glue_athena_list_query_executions_tool: {e}")
        return f"Error: {str(e)}"


async def glue_athena_batch_get_query_execution_tool(
    chicory_project_id: str,
    query_execution_ids: str
) -> str:
    """Batch get details of multiple Athena query executions."""
    try:
        if not await _check_provider_support(chicory_project_id, "glue"):
            return "Error: Glue integration is not configured for this project"

        provider = await get_provider(chicory_project_id, "glue")
        if not provider:
            return "Error: Could not get Glue provider for project"

        ids = [qe_id.strip() for qe_id in query_execution_ids.split(",")]
        result = await provider.athena_batch_get_query_execution(ids)

        if "error" in result:
            return f"Failed to batch get query executions: {result['error']}"

        executions = result.get("query_executions", [])
        output = f"Query Executions: {len(executions)}\n\n"

        for qe in executions:
            output += f"ID: {qe.get('query_execution_id')}\n"
            output += f"  State: {qe.get('state')}\n"
            output += f"  Workgroup: {qe.get('work_group', 'N/A')}\n"
            output += f"  Submitted: {qe.get('submission_date_time', 'N/A')}\n"
            output += f"  Completed: {qe.get('completion_date_time', 'N/A')}\n\n"

        unprocessed = result.get("unprocessed_query_execution_ids", [])
        if unprocessed:
            output += f"\nUnprocessed IDs: {', '.join(unprocessed)}"

        return output if executions else "No query executions found"

    except Exception as e:
        logger.error(f"Error in glue_athena_batch_get_query_execution_tool: {e}")
        return f"Error: {str(e)}"


@mcp.custom_route("/mcp/{project_id}", methods=["GET", "POST"])
async def project_mcp_endpoint(request: Request) -> JSONResponse:
    """
    Project-specific MCP endpoint that filters tools based on project integrations.
    Path parameter: project_id
    
    This endpoint acts as a proxy to the main MCP server but only exposes
    tools that are supported by the project's configured integrations.
    """
    try:
        project_id = request.path_params.get("project_id")
        if not project_id:
            return JSONResponse(
                content={"error": "project_id path parameter is required"}, 
                status_code=400
            )
        
        # Get supported providers for the project
        supported_providers = await get_supported_providers(project_id)
        available_tool_names = await get_available_tools_for_project(project_id)
        
        # Handle MCP protocol requests
        if request.method == "POST":
            try:
                body = await request.json()
                method = body.get("method")
                
                if method == "initialize":
                    # Handle MCP initialization handshake
                    return JSONResponse(content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "db-mcp-server",
                                "version": "1.0.0"
                            }
                        }
                    })
                
                elif method == "notifications/initialized":
                    # Handle initialization complete notification
                    # This is a notification, so no response is required per JSON-RPC 2.0 spec
                    logger.info(f"Client initialized for project {project_id}")
                    return JSONResponse(content={}, status_code=200)
                
                elif method == "tools/list":
                    # Return only tools available for this project
                    tools = []
                    
                    # Define full tool schemas for supported tools
                    all_tool_schemas = {
                        "databricks_query_tool": {
                            "name": "databricks_query_tool",
                            "description": "Execute any SQL query against a Databricks database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "catalog": {"type": "string", "description": "Databricks catalog name"},
                                    "schema": {"type": "string", "description": "Databricks schema name"},
                                    "query": {"type": "string", "description": "SQL query to execute"},
                                    "limit": {"type": "integer", "description": "Maximum number of rows to return", "default": 100}
                                },
                                "required": ["catalog", "schema", "query"]
                            }
                        },
                        "databricks_list_tables_tool": {
                            "name": "databricks_list_tables_tool", 
                            "description": "List tables in a Databricks schema using SHOW TABLES",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "catalog": {"type": "string", "description": "Databricks catalog name"},
                                    "schema_name": {"type": "string", "description": "Schema name to list tables from"}
                                },
                                "required": ["catalog", "schema_name"]
                            }
                        },
                        "databricks_describe_table_tool": {
                            "name": "databricks_describe_table_tool",
                            "description": "Get schema information for a specific table using DESCRIBE",
                            "inputSchema": {
                                "type": "object", 
                                "properties": {
                                    "catalog": {"type": "string", "description": "Databricks catalog name"},
                                    "schema_name": {"type": "string", "description": "Schema name"},
                                    "table_name": {"type": "string", "description": "Table name to describe"}
                                },
                                "required": ["catalog", "schema_name", "table_name"]
                            }
                        },
                        "databricks_sample_table_tool": {
                            "name": "databricks_sample_table_tool",
                            "description": "Sample data from a specific table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "catalog": {"type": "string", "description": "Databricks catalog name"},
                                    "schema_name": {"type": "string", "description": "Schema name"},
                                    "table_name": {"type": "string", "description": "Table name to sample"},
                                    "limit": {"type": "integer", "description": "Number of sample rows to return", "default": 10}
                                },
                                "required": ["catalog", "schema_name", "table_name"]
                            }
                        },
                        # Snowflake tools
                        "snowflake_query_tool": {
                            "name": "snowflake_query_tool",
                            "description": "Execute a SQL query against a Snowflake database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database": {"type": "string", "description": "Snowflake database name"},
                                    "schema": {"type": "string", "description": "Snowflake schema name"},
                                    "query": {"type": "string", "description": "SQL query to execute"},
                                    "limit": {"type": "integer", "description": "Maximum number of rows to return", "default": 100}
                                },
                                "required": ["database", "schema", "query"]
                            }
                        },
                        "snowflake_list_tables_tool": {
                            "name": "snowflake_list_tables_tool",
                            "description": "List tables in a Snowflake database and schema",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database": {"type": "string", "description": "Database name"},
                                    "schema": {"type": "string", "description": "Schema name"}
                                },
                                "required": ["database", "schema"]
                            }
                        },
                        "snowflake_describe_table_tool": {
                            "name": "snowflake_describe_table_tool",
                            "description": "Get schema information for a Snowflake table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database": {"type": "string", "description": "Database name"},
                                    "schema": {"type": "string", "description": "Schema name"},
                                    "table_name": {"type": "string", "description": "Name of the table to describe"}
                                },
                                "required": ["database", "schema", "table_name"]
                            }
                        },
                        "snowflake_sample_table_tool": {
                            "name": "snowflake_sample_table_tool",
                            "description": "Sample data from a Snowflake table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database": {"type": "string", "description": "Database name"},
                                    "schema": {"type": "string", "description": "Schema name"},
                                    "table_name": {"type": "string", "description": "Name of the table to sample"},
                                    "limit": {"type": "integer", "description": "Number of rows to sample", "default": 10}
                                },
                                "required": ["database", "schema", "table_name"]
                            }
                        },
                        # BigQuery tools
                        "bigquery_query_tool": {
                            "name": "bigquery_query_tool",
                            "description": "Execute a SQL query against a BigQuery database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset": {"type": "string", "description": "BigQuery dataset name"},
                                    "query": {"type": "string", "description": "SQL query to execute"},
                                    "limit": {"type": "integer", "description": "Maximum number of rows to return", "default": 100}
                                },
                                "required": ["dataset", "query"]
                            }
                        },
                        "bigquery_list_tables_tool": {
                            "name": "bigquery_list_tables_tool",
                            "description": "List tables in BigQuery datasets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset": {"type": "string", "description": "Dataset name"}
                                },
                                "required": ["dataset"]
                            }
                        },
                        "bigquery_describe_table_tool": {
                            "name": "bigquery_describe_table_tool",
                            "description": "Get schema information for a BigQuery table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset": {"type": "string", "description": "Dataset name"},
                                    "table_id": {"type": "string", "description": "Table name"}
                                },
                                "required": ["dataset", "table_id"]
                            }
                        },
                        "bigquery_sample_table_tool": {
                            "name": "bigquery_sample_table_tool",
                            "description": "Sample data from a BigQuery table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset": {"type": "string", "description": "Dataset name"},
                                    "table_id": {"type": "string", "description": "Table name"},
                                    "limit": {"type": "integer", "description": "Number of rows to sample", "default": 10}
                                },
                                "required": ["dataset", "table_id"]
                            }
                        },
                        # Redshift tools
                        "redshift_query_tool": {
                            "name": "redshift_query_tool",
                            "description": "Execute a SQL query against a Redshift database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "SQL query to execute"},
                                    "limit": {"type": "integer", "description": "Maximum number of rows to return", "default": 100}
                                },
                                "required": ["query"]
                            }
                        },
                        "redshift_list_tables_tool": {
                            "name": "redshift_list_tables_tool",
                            "description": "List tables in Redshift schemas",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "schema": {"type": "string", "description": "Schema name (optional, lists from public schema if not provided)"}
                                },
                                "required": []
                            }
                        },
                        "redshift_describe_table_tool": {
                            "name": "redshift_describe_table_tool",
                            "description": "Get schema information for a Redshift table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "Name of the table to describe"},
                                    "schema": {"type": "string", "description": "Schema name (optional, uses public if not provided)"}
                                },
                                "required": ["table_name"]
                            }
                        },
                        "redshift_sample_table_tool": {
                            "name": "redshift_sample_table_tool",
                            "description": "Sample data from a Redshift table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "Name of the table to sample"},
                                    "schema": {"type": "string", "description": "Schema name (optional, uses public if not provided)"},
                                    "limit": {"type": "integer", "description": "Number of rows to sample", "default": 10}
                                },
                                "required": ["table_name"]
                            }
                        },
                        # Glue tools
                        "glue_list_databases_tool": {
                            "name": "glue_list_databases_tool",
                            "description": "List all databases in AWS Glue Data Catalog",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "glue_list_tables_tool": {
                            "name": "glue_list_tables_tool",
                            "description": "List tables in an AWS Glue database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name in Glue Data Catalog"}
                                },
                                "required": ["database_name"]
                            }
                        },
                        "glue_describe_table_tool": {
                            "name": "glue_describe_table_tool",
                            "description": "Get schema information for an AWS Glue table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name in Glue Data Catalog"},
                                    "table_name": {"type": "string", "description": "Table name to describe"}
                                },
                                "required": ["database_name", "table_name"]
                            }
                        },
                        "glue_get_partitions_tool": {
                            "name": "glue_get_partitions_tool",
                            "description": "Get partitions for an AWS Glue table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name in Glue Data Catalog"},
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "max_results": {"type": "integer", "description": "Maximum number of partitions to return", "default": 100}
                                },
                                "required": ["database_name", "table_name"]
                            }
                        },
                        # Glue Data Quality tools
                        "glue_create_data_quality_ruleset_tool": {
                            "name": "glue_create_data_quality_ruleset_tool",
                            "description": "Create a data quality ruleset for an AWS Glue table using DQDL (Data Quality Definition Language)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the data quality ruleset"},
                                    "ruleset": {"type": "string", "description": "Data quality rules in DQDL format"},
                                    "database_name": {"type": "string", "description": "Target database name"},
                                    "table_name": {"type": "string", "description": "Target table name"},
                                    "description": {"type": "string", "description": "Optional description of the ruleset"}
                                },
                                "required": ["name", "ruleset", "database_name", "table_name"]
                            }
                        },
                        "glue_get_data_quality_ruleset_tool": {
                            "name": "glue_get_data_quality_ruleset_tool",
                            "description": "Get details of a data quality ruleset by name",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the data quality ruleset"}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_update_data_quality_ruleset_tool": {
                            "name": "glue_update_data_quality_ruleset_tool",
                            "description": "Update an existing data quality ruleset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the data quality ruleset"},
                                    "ruleset": {"type": "string", "description": "Updated data quality rules in DQDL format"},
                                    "description": {"type": "string", "description": "Updated description"}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_delete_data_quality_ruleset_tool": {
                            "name": "glue_delete_data_quality_ruleset_tool",
                            "description": "Delete a data quality ruleset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the data quality ruleset to delete"}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_list_data_quality_rulesets_tool": {
                            "name": "glue_list_data_quality_rulesets_tool",
                            "description": "List data quality rulesets, optionally filtered by target table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Filter by database name"},
                                    "table_name": {"type": "string", "description": "Filter by table name"},
                                    "max_results": {"type": "integer", "description": "Maximum number of rulesets to return", "default": 100}
                                },
                                "required": []
                            }
                        },
                        "glue_start_data_quality_rule_recommendation_run_tool": {
                            "name": "glue_start_data_quality_rule_recommendation_run_tool",
                            "description": "Start an AI-powered data quality rule recommendation run for a Glue table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name"},
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "role": {"type": "string", "description": "IAM role ARN for the recommendation run"},
                                    "number_of_workers": {"type": "integer", "description": "Number of workers for the job", "default": 5}
                                },
                                "required": ["database_name", "table_name", "role"]
                            }
                        },
                        "glue_get_data_quality_rule_recommendation_run_tool": {
                            "name": "glue_get_data_quality_rule_recommendation_run_tool",
                            "description": "Get the status and results of a data quality rule recommendation run",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "run_id": {"type": "string", "description": "Run ID from start_data_quality_rule_recommendation_run"}
                                },
                                "required": ["run_id"]
                            }
                        },
                        "glue_start_data_quality_ruleset_evaluation_run_tool": {
                            "name": "glue_start_data_quality_ruleset_evaluation_run_tool",
                            "description": "Start a data quality ruleset evaluation run against a Glue table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name"},
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "ruleset_names": {"type": "string", "description": "Comma-separated list of ruleset names to evaluate"},
                                    "role": {"type": "string", "description": "IAM role ARN for the evaluation run"},
                                    "number_of_workers": {"type": "integer", "description": "Number of workers for the job", "default": 5}
                                },
                                "required": ["database_name", "table_name", "ruleset_names", "role"]
                            }
                        },
                        "glue_get_data_quality_ruleset_evaluation_run_tool": {
                            "name": "glue_get_data_quality_ruleset_evaluation_run_tool",
                            "description": "Get the status and results of a data quality ruleset evaluation run",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "run_id": {"type": "string", "description": "Run ID from start_data_quality_ruleset_evaluation_run"}
                                },
                                "required": ["run_id"]
                            }
                        },
                        "glue_list_data_quality_results_tool": {
                            "name": "glue_list_data_quality_results_tool",
                            "description": "List data quality evaluation results, optionally filtered by table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Filter by database name"},
                                    "table_name": {"type": "string", "description": "Filter by table name"},
                                    "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 100}
                                },
                                "required": []
                            }
                        },
                        # Glue Column Statistics tools
                        "glue_get_column_statistics_for_table_tool": {
                            "name": "glue_get_column_statistics_for_table_tool",
                            "description": "Get column statistics for specified columns in a Glue table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name"},
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "column_names": {"type": "string", "description": "Comma-separated list of column names"}
                                },
                                "required": ["database_name", "table_name", "column_names"]
                            }
                        },
                        "glue_get_column_statistics_for_partition_tool": {
                            "name": "glue_get_column_statistics_for_partition_tool",
                            "description": "Get column statistics for specified columns in a Glue table partition",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name"},
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "partition_values": {"type": "string", "description": "Comma-separated partition values"},
                                    "column_names": {"type": "string", "description": "Comma-separated list of column names"}
                                },
                                "required": ["database_name", "table_name", "partition_values", "column_names"]
                            }
                        },
                        "glue_delete_column_statistics_for_table_tool": {
                            "name": "glue_delete_column_statistics_for_table_tool",
                            "description": "Delete column statistics for a specific column in a Glue table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name"},
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "column_name": {"type": "string", "description": "Column name"}
                                },
                                "required": ["database_name", "table_name", "column_name"]
                            }
                        },
                        "glue_delete_column_statistics_for_partition_tool": {
                            "name": "glue_delete_column_statistics_for_partition_tool",
                            "description": "Delete column statistics for a specific column in a Glue table partition",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "database_name": {"type": "string", "description": "Database name"},
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "partition_values": {"type": "string", "description": "Comma-separated partition values"},
                                    "column_name": {"type": "string", "description": "Column name"}
                                },
                                "required": ["database_name", "table_name", "partition_values", "column_name"]
                            }
                        },
                        # Athena tools
                        "glue_athena_create_work_group_tool": {
                            "name": "glue_athena_create_work_group_tool",
                            "description": "Create an Athena workgroup",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the workgroup"},
                                    "description": {"type": "string", "description": "Optional description of the workgroup"}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_athena_list_work_groups_tool": {
                            "name": "glue_athena_list_work_groups_tool",
                            "description": "List all Athena workgroups",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "max_results": {"type": "integer", "description": "Maximum number of workgroups to return", "default": 50}
                                },
                                "required": []
                            }
                        },
                        "glue_athena_get_work_group_tool": {
                            "name": "glue_athena_get_work_group_tool",
                            "description": "Get details of an Athena workgroup",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the workgroup"}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_athena_update_work_group_tool": {
                            "name": "glue_athena_update_work_group_tool",
                            "description": "Update an Athena workgroup",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the workgroup"},
                                    "description": {"type": "string", "description": "Updated description"},
                                    "state": {"type": "string", "description": "Updated state (ENABLED or DISABLED)"}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_athena_delete_work_group_tool": {
                            "name": "glue_athena_delete_work_group_tool",
                            "description": "Delete an Athena workgroup",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the workgroup"},
                                    "recursive_delete": {"type": "boolean", "description": "If true, deletes the workgroup and its contents", "default": False}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_athena_get_data_catalog_tool": {
                            "name": "glue_athena_get_data_catalog_tool",
                            "description": "Get details of an Athena data catalog",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the data catalog"}
                                },
                                "required": ["name"]
                            }
                        },
                        "glue_athena_list_data_catalogs_tool": {
                            "name": "glue_athena_list_data_catalogs_tool",
                            "description": "List all Athena data catalogs",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "max_results": {"type": "integer", "description": "Maximum number of catalogs to return", "default": 50}
                                },
                                "required": []
                            }
                        },
                        "glue_athena_update_data_catalog_tool": {
                            "name": "glue_athena_update_data_catalog_tool",
                            "description": "Update an Athena data catalog",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the data catalog"},
                                    "type": {"type": "string", "description": "Type of the data catalog (GLUE, LAMBDA, HIVE)"},
                                    "description": {"type": "string", "description": "Optional description"}
                                },
                                "required": ["name", "type"]
                            }
                        },
                        "glue_athena_start_query_execution_tool": {
                            "name": "glue_athena_start_query_execution_tool",
                            "description": "Start an Athena query execution",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_string": {"type": "string", "description": "SQL query string to execute"},
                                    "database": {"type": "string", "description": "Optional database name"},
                                    "output_location": {"type": "string", "description": "Optional S3 output location"},
                                    "work_group": {"type": "string", "description": "Optional workgroup name"}
                                },
                                "required": ["query_string"]
                            }
                        },
                        "glue_athena_get_query_execution_tool": {
                            "name": "glue_athena_get_query_execution_tool",
                            "description": "Get details of an Athena query execution",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_execution_id": {"type": "string", "description": "Query execution ID"}
                                },
                                "required": ["query_execution_id"]
                            }
                        },
                        "glue_athena_stop_query_execution_tool": {
                            "name": "glue_athena_stop_query_execution_tool",
                            "description": "Stop an Athena query execution",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_execution_id": {"type": "string", "description": "Query execution ID"}
                                },
                                "required": ["query_execution_id"]
                            }
                        },
                        "glue_athena_get_query_results_tool": {
                            "name": "glue_athena_get_query_results_tool",
                            "description": "Get results of an Athena query execution",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_execution_id": {"type": "string", "description": "Query execution ID"},
                                    "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 1000}
                                },
                                "required": ["query_execution_id"]
                            }
                        },
                        "glue_athena_list_query_executions_tool": {
                            "name": "glue_athena_list_query_executions_tool",
                            "description": "List Athena query executions",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "work_group": {"type": "string", "description": "Optional workgroup name to filter by"},
                                    "max_results": {"type": "integer", "description": "Maximum number of query executions to return", "default": 50}
                                },
                                "required": []
                            }
                        },
                        "glue_athena_batch_get_query_execution_tool": {
                            "name": "glue_athena_batch_get_query_execution_tool",
                            "description": "Batch get details of multiple Athena query executions",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_execution_ids": {"type": "string", "description": "Comma-separated list of query execution IDs"}
                                },
                                "required": ["query_execution_ids"]
                            }
                        }
                    }
                    
                    # Only include tools that are available for this project
                    for tool_name in available_tool_names:
                        if tool_name in all_tool_schemas:
                            tools.append(all_tool_schemas[tool_name])
                    
                    return JSONResponse(content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "tools": tools
                        }
                    })
                
                elif method == "tools/call":
                    # Handle tool calls - validate that the tool is available for this project
                    params = body.get("params", {})
                    tool_name = params.get("name")
                    tool_arguments = params.get("arguments", {})
                    
                    if tool_name not in available_tool_names:
                        return JSONResponse(content={
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "error": {
                                "code": -32601,
                                "message": f"Tool '{tool_name}' is not available for project '{project_id}'. Available tools: {available_tool_names}"
                            }
                        })
                    
                    # Inject chicory_project_id into tool arguments
                    tool_arguments["chicory_project_id"] = project_id
                    
                    # Map tool names to their actual functions
                    tool_functions = {
                        "databricks_query_tool": databricks_query_tool,
                        "databricks_list_tables_tool": databricks_list_tables_tool,
                        "databricks_describe_table_tool": databricks_describe_table_tool,
                        "databricks_sample_table_tool": databricks_sample_table_tool,
                        "snowflake_query_tool": snowflake_query_tool,
                        "snowflake_list_tables_tool": snowflake_list_tables_tool,
                        "snowflake_describe_table_tool": snowflake_describe_table_tool,
                        "snowflake_sample_table_tool": snowflake_sample_table_tool,
                        "bigquery_query_tool": bigquery_query_tool,
                        "bigquery_list_tables_tool": bigquery_list_tables_tool,
                        "bigquery_describe_table_tool": bigquery_describe_table_tool,
                        "bigquery_sample_table_tool": bigquery_sample_table_tool,
                        "redshift_query_tool": redshift_query_tool,
                        "redshift_list_tables_tool": redshift_list_tables_tool,
                        "redshift_describe_table_tool": redshift_describe_table_tool,
                        "redshift_sample_table_tool": redshift_sample_table_tool,
                        "glue_list_databases_tool": glue_list_databases_tool,
                        "glue_list_tables_tool": glue_list_tables_tool,
                        "glue_describe_table_tool": glue_describe_table_tool,
                        "glue_get_partitions_tool": glue_get_partitions_tool,
                        "glue_create_data_quality_ruleset_tool": glue_create_data_quality_ruleset_tool,
                        "glue_get_data_quality_ruleset_tool": glue_get_data_quality_ruleset_tool,
                        "glue_update_data_quality_ruleset_tool": glue_update_data_quality_ruleset_tool,
                        "glue_delete_data_quality_ruleset_tool": glue_delete_data_quality_ruleset_tool,
                        "glue_list_data_quality_rulesets_tool": glue_list_data_quality_rulesets_tool,
                        "glue_start_data_quality_rule_recommendation_run_tool": glue_start_data_quality_rule_recommendation_run_tool,
                        "glue_get_data_quality_rule_recommendation_run_tool": glue_get_data_quality_rule_recommendation_run_tool,
                        "glue_start_data_quality_ruleset_evaluation_run_tool": glue_start_data_quality_ruleset_evaluation_run_tool,
                        "glue_get_data_quality_ruleset_evaluation_run_tool": glue_get_data_quality_ruleset_evaluation_run_tool,
                        "glue_list_data_quality_results_tool": glue_list_data_quality_results_tool,
                        "glue_get_column_statistics_for_table_tool": glue_get_column_statistics_for_table_tool,
                        "glue_get_column_statistics_for_partition_tool": glue_get_column_statistics_for_partition_tool,
                        "glue_delete_column_statistics_for_table_tool": glue_delete_column_statistics_for_table_tool,
                        "glue_delete_column_statistics_for_partition_tool": glue_delete_column_statistics_for_partition_tool,
                        "glue_athena_create_work_group_tool": glue_athena_create_work_group_tool,
                        "glue_athena_list_work_groups_tool": glue_athena_list_work_groups_tool,
                        "glue_athena_get_work_group_tool": glue_athena_get_work_group_tool,
                        "glue_athena_update_work_group_tool": glue_athena_update_work_group_tool,
                        "glue_athena_delete_work_group_tool": glue_athena_delete_work_group_tool,
                        "glue_athena_get_data_catalog_tool": glue_athena_get_data_catalog_tool,
                        "glue_athena_list_data_catalogs_tool": glue_athena_list_data_catalogs_tool,
                        "glue_athena_update_data_catalog_tool": glue_athena_update_data_catalog_tool,
                        "glue_athena_start_query_execution_tool": glue_athena_start_query_execution_tool,
                        "glue_athena_get_query_execution_tool": glue_athena_get_query_execution_tool,
                        "glue_athena_stop_query_execution_tool": glue_athena_stop_query_execution_tool,
                        "glue_athena_get_query_results_tool": glue_athena_get_query_results_tool,
                        "glue_athena_list_query_executions_tool": glue_athena_list_query_executions_tool,
                        "glue_athena_batch_get_query_execution_tool": glue_athena_batch_get_query_execution_tool,
                    }
                    
                    # Execute the tool
                    try:
                        tool_func = tool_functions.get(tool_name)
                        if not tool_func:
                            return JSONResponse(content={
                                "jsonrpc": "2.0",
                                "id": body.get("id"),
                                "error": {
                                    "code": -32601,
                                    "message": f"Tool function not found: {tool_name}"
                                }
                            })
                        
                        # Call the tool function with injected project_id
                        result = await tool_func(**tool_arguments)
                        
                        return JSONResponse(content={
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": result
                                    }
                                ]
                            }
                        })
                        
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                        return JSONResponse(content={
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "error": {
                                "code": -32603,
                                "message": f"Tool execution failed: {str(e)}"
                            }
                        })
                
                else:
                    return JSONResponse(content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method '{method}' not supported"
                        }
                    })
                    
            except Exception as e:
                logger.error(f"Error processing MCP request: {e}")
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": body.get("id") if 'body' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                })
        
        # Handle GET requests - return project info
        else:
            return JSONResponse(content={
                "project_id": project_id,
                "supported_providers": supported_providers,
                "available_tools": available_tool_names,
                "total_tools": len(available_tool_names),
                "mcp_endpoint": f"/mcp/{project_id}"
            })
        
    except Exception as e:
        logger.error(f"Error in project_mcp_endpoint: {e}")
        return JSONResponse(
            content={"error": f"Internal server error: {str(e)}"}, 
            status_code=500
        )


@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> JSONResponse:
    """
    HTTP health check endpoint for monitoring, load balancers, and Docker health checks.
    
    Returns:
        JSON response with server health status
    """
    try:
        # Basic health check - verify server components are responsive
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "server": "db-mcp-server",
            "version": "1.0.0",
            "components": {
                "cache_manager": "active" if cache_manager else "inactive",
                "credential_fetcher": "active" if credential_fetcher else "inactive"
            }
        }
        
        return JSONResponse(content=status, status_code=200)
        
    except Exception as e:
        logger.error(f"Health endpoint failed: {e}")
        error_status = {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
        return JSONResponse(content=error_status, status_code=503)


async def get_available_tools_for_project(project_id: str) -> List[str]:
    """
    Get list of available tool names for a specific project based on supported integrations.
    
    Args:
        project_id: Project identifier
        
    Returns:
        List of tool names available for the project
    """
    supported_providers = await get_supported_providers(project_id)
    
    # Define tool name mappings
    tool_name_mappings = {
        "databricks": [
            "databricks_query_tool",
            "databricks_list_tables_tool",
            "databricks_describe_table_tool",
            "databricks_sample_table_tool"
        ],
        "snowflake": [
            "snowflake_query_tool",
            "snowflake_list_tables_tool",
            "snowflake_describe_table_tool",
            "snowflake_sample_table_tool"
        ],
        "bigquery": [
            "bigquery_query_tool",
            "bigquery_list_tables_tool",
            "bigquery_describe_table_tool",
            "bigquery_sample_table_tool"
        ],
        "redshift": [
            "redshift_query_tool",
            "redshift_list_tables_tool",
            "redshift_describe_table_tool",
            "redshift_sample_table_tool"
        ],
        "glue": [
            "glue_list_databases_tool",
            "glue_list_tables_tool",
            "glue_describe_table_tool",
            "glue_get_partitions_tool",
            "glue_create_data_quality_ruleset_tool",
            "glue_get_data_quality_ruleset_tool",
            "glue_update_data_quality_ruleset_tool",
            "glue_delete_data_quality_ruleset_tool",
            "glue_list_data_quality_rulesets_tool",
            "glue_start_data_quality_rule_recommendation_run_tool",
            "glue_get_data_quality_rule_recommendation_run_tool",
            "glue_start_data_quality_ruleset_evaluation_run_tool",
            "glue_get_data_quality_ruleset_evaluation_run_tool",
            "glue_list_data_quality_results_tool",
            "glue_get_column_statistics_for_table_tool",
            "glue_get_column_statistics_for_partition_tool",
            "glue_delete_column_statistics_for_table_tool",
            "glue_delete_column_statistics_for_partition_tool",
            "glue_athena_create_work_group_tool",
            "glue_athena_list_work_groups_tool",
            "glue_athena_get_work_group_tool",
            "glue_athena_update_work_group_tool",
            "glue_athena_delete_work_group_tool",
            "glue_athena_get_data_catalog_tool",
            "glue_athena_list_data_catalogs_tool",
            "glue_athena_update_data_catalog_tool",
            "glue_athena_start_query_execution_tool",
            "glue_athena_get_query_execution_tool",
            "glue_athena_stop_query_execution_tool",
            "glue_athena_get_query_results_tool",
            "glue_athena_list_query_executions_tool",
            "glue_athena_batch_get_query_execution_tool"
        ]
    }

    # Build available tools list
    available_tools = []
    for provider in supported_providers:
        if provider in tool_name_mappings:
            available_tools.extend(tool_name_mappings[provider])
    
    logger.info(f"Available tools for project {project_id}: {available_tools}")
    return available_tools


async def cleanup():
    """Cleanup resources on server shutdown."""
    logger.info("Cleaning up database connections...")
    cache_manager.cleanup()
    logger.info("Cleanup completed")


if __name__ == "__main__":
    # Setup cleanup on shutdown
    import signal
    
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(cleanup())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting DB MCP Server on 0.0.0.0:8080")
    
    # Run the FastMCP server with HTTP transport (streamable)
    mcp.run(transport="streamable-http")

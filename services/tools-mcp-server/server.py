#!/usr/bin/env python3
"""
Tools MCP Server - A Model Context Protocol server for tools.

Provides tools for interacting with Looker, Redash, and OpenAPI services with
project-based credential management and connection caching.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from providers import ToolsProvider
from providers.looker import LookerProvider
from providers.redash import RedashProvider
from providers.openapi import OpenAPIProvider
from providers.dbt import DbtProvider
from providers.datahub import DataHubProvider
from providers.airflow import AirflowProvider
from providers.datazone import DatazoneProvider
from providers.s3 import S3Provider
from providers.jira import JiraProvider
from providers.azure_blob_storage import AzureBlobStorageProvider
from providers.azure_data_factory import AzureDataFactoryProvider
from providers.atlan import AtlanProvider
from config import Config
from cache_manager import ConnectionCacheManager
from credential_fetcher import CredentialFetcher
from tools.jira_tools import *

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("ToolsMCPServer", host="0.0.0.0", port=8080)

# Global instances
config = Config()
cache_manager = ConnectionCacheManager(
    ttl_seconds=config.CONNECTION_CACHE_TTL,
    max_size=config.CONNECTION_CACHE_MAX_SIZE
)
credential_fetcher = CredentialFetcher(config.API_BASE_URL)

# Provider registry - store classes, not instances
providers: Dict[str, type] = {
    "looker": LookerProvider,
    "redash": RedashProvider,
    "openapi": OpenAPIProvider,
    "dbt": DbtProvider,
    "datahub": DataHubProvider,
    "airflow": AirflowProvider,
    "datazone": DatazoneProvider,
    "s3": S3Provider,
    "jira": JiraProvider,
    "azure_blob_storage": AzureBlobStorageProvider,
    "azure_data_factory": AzureDataFactoryProvider,
    "atlan": AtlanProvider,
}



async def get_supported_tool_providers(project_id: str) -> List[str]:
    """
    Get list of supported tool provider types for a project.
    
    Args:
        project_id: Project identifier
        
    Returns:
        List of supported provider type names
    """
    try:
        all_data_sources = await credential_fetcher.get_all_data_sources(project_id)
        logger.info(f"Fetched {len(all_data_sources)} total data sources for project {project_id}")
        logger.debug(f"Data source types from API: {[ds.get('type') for ds in all_data_sources]}")
        logger.debug(f"Registered providers in server: {list(providers.keys())}")

        supported = [ds.get("type") for ds in all_data_sources if ds.get("type") in providers]
        
        logger.info(f"Detected tool providers for project {project_id}: {supported}")
        return supported
    except Exception as e:
        logger.error(f"Error fetching tool providers for project {project_id}: {e}", exc_info=True)
        return []


async def _check_tool_provider_support(project_id: str, provider_type: str) -> bool:
    """
    Check if a specific tool provider type is supported for a project.
    
    Args:
        project_id: Project identifier
        provider_type: Provider type to check
        
    Returns:
        True if provider is supported, False otherwise
    """
    supported_providers = await get_supported_tool_providers(project_id)
    return provider_type in supported_providers


async def get_available_tools_for_project(project_id: str) -> List[str]:
    """
    Get list of available tool names for a project based on configured integrations.
    
    Args:
        project_id: Project identifier
        
    Returns:
        List of available tool names
    """
    supported_providers = await get_supported_tool_providers(project_id)
    available_tools = []
    
    # Map providers to their tools
    tool_mappings = {
        "looker": [
            "looker_get_models_tool", "looker_get_explores_tool",
            "looker_get_dimensions_tool", "looker_get_measures_tool",
            "looker_get_filters_tool", "looker_query_tool",
            "looker_query_sql_tool", "looker_get_looks_tool",
            "looker_run_look_tool", "looker_query_url_tool"
        ],
        "redash": [
            "redash_list_queries_tool", "redash_get_query_tool",
            "redash_execute_query_tool", "redash_get_query_job_status_tool",
            "redash_get_query_results_tool", "redash_refresh_query_tool",
            "redash_list_dashboards_tool", "redash_get_dashboard_tool",
            "redash_list_data_sources_tool", "redash_create_query_tool",
            "redash_create_visualization_tool", "redash_create_dashboard_tool",
            "redash_add_widget_tool", "redash_publish_dashboard_tool"
        ],
        "dbt": [
            "dbt_list_projects_tool", "dbt_list_environments_tool",
            "dbt_list_jobs_tool", "dbt_trigger_job_run_tool",
            "dbt_get_job_run_tool", "dbt_list_job_runs_tool",
            "dbt_cancel_job_run_tool", "dbt_list_models_tool",
            "dbt_get_model_details_tool", "dbt_list_metrics_tool",
            "dbt_query_metrics_tool", "dbt_execute_sql_tool"
        ],
        "datahub": [
            "datahub_search_entities_tool", "datahub_get_entity_tool",
            "datahub_list_datasets_tool", "datahub_list_dashboards_tool",
            "datahub_list_charts_tool", "datahub_get_lineage_tool",
            "datahub_list_platforms_tool", "datahub_list_tags_tool"
        ],
        "airflow": [
            "airflow_list_dags_tool", "airflow_get_dag_tool",
            "airflow_trigger_dag_tool", "airflow_get_dag_runs_tool",
            "airflow_get_task_instances_tool", "airflow_get_task_logs_tool",
            "airflow_pause_dag_tool", "airflow_unpause_dag_tool"
        ],
        "openapi": [
            "openapi_get_spec_tool", "openapi_list_endpoints_tool",
            "openapi_call_endpoint_tool", "openapi_get_endpoint_schema_tool"
        ],
        "datazone": [
            "datazone_list_domains_tool", "datazone_get_domain_tool",
            "datazone_list_projects_tool", "datazone_get_project_tool",
            "datazone_search_listings_tool", "datazone_get_listing_tool",
            "datazone_list_environments_tool", "datazone_get_environment_tool",
            "datazone_get_asset_tool", "datazone_list_asset_revisions_tool",
            "datazone_get_glossary_tool", "datazone_get_glossary_term_tool",
            "datazone_create_form_type_tool", "datazone_get_form_type_tool",
            "datazone_create_asset_type_tool", "datazone_get_asset_type_tool",
            "datazone_list_asset_types_tool"
        ],
        "s3": [
            "s3_list_buckets_tool", "s3_list_objects_tool",
            "s3_get_object_tool", "s3_get_object_metadata_tool",
            "s3_create_bucket_tool", "s3_put_object_tool",
            "s3_generate_presigned_url_tool", "s3_generate_presigned_post_tool"
        ],
        "jira": [
            "jira_search_issues_tool", "jira_get_issue_tool",
            "jira_create_issue_tool", "jira_update_issue_tool",
            "jira_transition_issue_tool", "jira_get_transitions_tool",
            "jira_assign_issue_tool", "jira_list_projects_tool",
            "jira_get_project_tool", "jira_get_issue_types_tool",
            "jira_get_fields_tool", "jira_add_comment_tool",
            "jira_get_comments_tool", "jira_upload_attachment_tool",
            "jira_list_boards_tool", "jira_list_sprints_tool",
            "jira_get_sprint_tool", "jira_get_backlog_tool"
        ],
        "azure_blob_storage": [
            "azure_blob_list_containers_tool", "azure_blob_list_blobs_tool",
            "azure_blob_get_blob_tool", "azure_blob_get_blob_metadata_tool",
            "azure_blob_upload_blob_tool", "azure_blob_delete_blob_tool",
            "azure_blob_generate_sas_url_tool", "azure_blob_get_container_properties_tool"
        ],
        "azure_data_factory": [
            "azure_adf_list_pipelines_tool", "azure_adf_get_pipeline_tool",
            "azure_adf_run_pipeline_tool", "azure_adf_get_pipeline_run_tool",
            "azure_adf_list_pipeline_runs_tool", "azure_adf_list_datasets_tool",
            "azure_adf_get_dataset_tool", "azure_adf_list_triggers_tool",
            "azure_adf_get_trigger_tool", "azure_adf_list_linked_services_tool",
            "azure_adf_get_linked_service_tool", "azure_adf_list_data_flows_tool",
            "azure_adf_get_data_flow_tool", "azure_adf_list_integration_runtimes_tool",
            "azure_adf_get_integration_runtime_tool", "azure_adf_get_factory_info_tool"
        ],
        "atlan": [
            "atlan_search_assets_tool", "atlan_search_by_type_tool",
            "atlan_get_asset_tool", "atlan_get_asset_by_qualified_name_tool",
            "atlan_create_asset_tool", "atlan_update_asset_tool", "atlan_delete_asset_tool",
            "atlan_update_asset_description_tool", "atlan_update_asset_owners_tool",
            "atlan_get_lineage_tool",
            "atlan_list_glossaries_tool", "atlan_get_glossary_tool",
            "atlan_list_glossary_terms_tool", "atlan_get_glossary_term_tool",
            "atlan_create_glossary_term_tool", "atlan_list_glossary_categories_tool",
            "atlan_link_term_to_asset_tool",
            "atlan_list_classifications_tool", "atlan_add_classification_tool",
            "atlan_remove_classification_tool",
            "atlan_list_tables_tool", "atlan_list_columns_tool",
            "atlan_list_databases_tool", "atlan_list_schemas_tool",
            "atlan_list_dashboards_tool", "atlan_list_dbt_models_tool",
            "atlan_list_airflow_dags_tool", "atlan_list_kafka_topics_tool",
            "atlan_list_s3_objects_tool",
            "atlan_update_custom_metadata_tool", "atlan_get_custom_metadata_types_tool",
            "atlan_certify_asset_tool", "atlan_bulk_update_assets_tool"
        ]
    }

    for provider in supported_providers:
        if provider in tool_mappings:
            available_tools.extend(tool_mappings[provider])
    
    logger.info(f"Available tools for project {project_id}: {len(available_tools)} tools from {len(supported_providers)} providers")
    return available_tools


async def get_tools_client(project_id: str, provider_name: Optional[str] = None) -> ToolsProvider:
    """
    Get or create a cached tools client for the specified project.

    Args:
        project_id: Project identifier for credential lookup
        provider_name: Tools provider name (optional, auto-detected from credentials)

    Returns:
        ToolsProvider instance

    Raises:
        ValueError: If provider is not supported or credentials are invalid
    """
    # Check cache first
    cached_client = cache_manager.get_connection(project_id, provider_name)
    if cached_client:
        logger.info(f"Using cached tools client for project: {project_id}")
        return cached_client

    # Auto-detect a provider type if not specified
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
            raise ValueError(f"No supported tools provider found for project: {project_id}")

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
        raise ValueError(f"Unsupported tools provider: {provider_name}")

    # Create a new instance of the provider for this project
    provider_class = providers[provider_name]
    provider = provider_class()

    logger.info(f"Created {provider_name} provider instance, initializing with credentials")

    # Initialize provider with credentials
    config_data = credentials.get("configuration", credentials)
    logger.info(
        f"Initializing provider with config keys: {list(config_data.keys()) if isinstance(config_data, dict) else 'non-dict config'}")
    await provider.initialize(config_data)

    # Cache the client
    cache_manager.cache_connection(project_id, provider_name, provider)

    logger.info(f"Created and cached new {provider_name} client for project: {project_id}")
    return provider


async def get_provider(project_id: str, provider_type: str) -> Optional[ToolsProvider]:
    """
    Get an tools provider for the specified project and type.

    Args:
        project_id: Project identifier for credential lookup
        provider_type: Tools provider type (looker, redash, openapi)

    Returns:
        ToolsProvider instance or None if error
    """
    try:
        logger.info(f"Getting {provider_type} provider for project {project_id}")
        return await get_tools_client(project_id, provider_type)
    except Exception as e:
        logger.error(f"Error getting {provider_type} provider for project {project_id}: {e}", exc_info=True)
        return None


# =============================================================================
# LOOKER TOOLS
# =============================================================================

async def looker_get_models_tool(project_id: str) -> str:
    """
    Get all Looker models available in the instance.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of Looker models formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.get_models()

        if "error" in result:
            return f"Error getting models: {result['error']}"

        models = result.get('models', [])

        output = f"Looker Models: {len(models)} found\n\n"

        if models:
            for model in models:
                name = model.get('name', 'Unknown')
                project_name = model.get('project_name', 'Unknown')
                explores_count = len(model.get('explores', []))
                output += f"- {name} (Project: {project_name}, Explores: {explores_count})\n"
        else:
            output += "No models found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_get_models_tool: {e}")
        return f"Error: {str(e)}"


async def looker_get_explores_tool(project_id: str, model_name: str) -> str:
    """
    Get all explores for a specific Looker model.

    Args:
        project_id: Project ID for credential lookup
        model_name: Name of the model to get explores from

    Returns:
        List of explores formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.get_explores(model_name)

        if "error" in result:
            return f"Error getting explores: {result['error']}"

        explores = result.get('explores', [])

        output = f"Explores in model '{model_name}': {len(explores)} found\n\n"

        if explores:
            for explore in explores:
                name = explore.get('name', 'Unknown')
                label = explore.get('label', name)
                dimensions_count = len(explore.get('dimensions', []))
                measures_count = len(explore.get('measures', []))
                output += f"- {name} ({label}) - Dims: {dimensions_count}, Measures: {measures_count}\n"
        else:
            output += "No explores found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_get_explores_tool: {e}")
        return f"Error: {str(e)}"


async def looker_get_dimensions_tool(project_id: str, model_name: str, explore_name: str) -> str:
    """
    Get all dimensions for a specific explore.

    Args:
        project_id: Project ID for credential lookup
        model_name: Name of the model
        explore_name: Name of the explore

    Returns:
        List of dimensions formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.get_dimensions(model_name, explore_name)

        if "error" in result:
            return f"Error getting dimensions: {result['error']}"

        dimensions = result.get('dimensions', [])

        output = f"Dimensions in {model_name}/{explore_name}: {len(dimensions)} found\n\n"

        if dimensions:
            for dim in dimensions:
                name = dim.get('name', 'Unknown')
                label = dim.get('label', name)
                dim_type = dim.get('type', 'Unknown')
                output += f"- {name} ({label}) - Type: {dim_type}\n"
        else:
            output += "No dimensions found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_get_dimensions_tool: {e}")
        return f"Error: {str(e)}"


async def looker_get_measures_tool(project_id: str, model_name: str, explore_name: str) -> str:
    """
    Get all measures for a specific explore.

    Args:
        project_id: Project ID for credential lookup
        model_name: Name of the model
        explore_name: Name of the explore

    Returns:
        List of measures formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.get_measures(model_name, explore_name)

        if "error" in result:
            return f"Error getting measures: {result['error']}"

        measures = result.get('measures', [])

        output = f"Measures in {model_name}/{explore_name}: {len(measures)} found\n\n"

        if measures:
            for measure in measures:
                name = measure.get('name', 'Unknown')
                label = measure.get('label', name)
                measure_type = measure.get('type', 'Unknown')
                output += f"- {name} ({label}) - Type: {measure_type}\n"
        else:
            output += "No measures found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_get_measures_tool: {e}")
        return f"Error: {str(e)}"


async def looker_get_filters_tool(project_id: str, model_name: str, explore_name: str) -> str:
    """
    Get all filters for a specific explore.

    Args:
        project_id: Project ID for credential lookup
        model_name: Name of the model
        explore_name: Name of the explore

    Returns:
        List of filters formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.get_filters(model_name, explore_name)

        if "error" in result:
            return f"Error getting filters: {result['error']}"

        filters = result.get('filters', [])

        output = f"Filters in {model_name}/{explore_name}: {len(filters)} found\n\n"

        if filters:
            for filter_item in filters:
                name = filter_item.get('name', 'Unknown')
                label = filter_item.get('label', name)
                filter_type = filter_item.get('type', 'Unknown')
                output += f"- {name} ({label}) - Type: {filter_type}\n"
        else:
            output += "No filters found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_get_filters_tool: {e}")
        return f"Error: {str(e)}"


async def looker_query_tool(project_id: str, model_name: str, explore_name: str,
                            dimensions: List[str], measures: List[str],
                            filters: Optional[Dict[str, str]] = None, limit: int = 100) -> str:
    """
    Execute a Looker query.

    Args:
        project_id: Project ID for credential lookup
        model_name: Name of the model
        explore_name: Name of the explore
        dimensions: List of dimension names to include
        measures: List of measure names to include
        filters: Dictionary of filters to apply
        limit: Maximum number of rows to return

    Returns:
        Query results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.query(model_name, explore_name, dimensions, measures, filters, limit)

        if "error" in result:
            return f"Error executing query: {result['error']}"

        rows = result.get('rows', [])
        columns = result.get('columns', [])

        output = f"Looker Query Results\n"
        output += f"Model: {model_name}, Explore: {explore_name}\n"
        output += f"Dimensions: {', '.join(dimensions)}\n"
        output += f"Measures: {', '.join(measures)}\n"
        if filters:
            output += f"Filters: {filters}\n"
        output += f"Rows returned: {len(rows)}\n\n"

        if columns:
            output += f"Columns: {', '.join(columns)}\n\n"

        if rows:
            output += "Sample data:\n"
            for i, row in enumerate(rows[:10]):  # Show first 10 rows
                output += f"Row {i + 1}: {row}\n"

            if len(rows) > 10:
                output += f"... and {len(rows) - 10} more rows\n"
        else:
            output += "No data returned.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_query_tool: {e}")
        return f"Error: {str(e)}"


async def looker_query_sql_tool(project_id: str, sql: str) -> str:
    """
    Execute raw SQL against Looker's database connection.

    Args:
        project_id: Project ID for credential lookup
        sql: SQL query to execute

    Returns:
        Query results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.query_sql(sql)

        if "error" in result:
            return f"Error executing SQL: {result['error']}"

        rows = result.get('rows', [])
        columns = result.get('columns', [])

        output = f"SQL Query Results\n"
        output += f"Query: {sql[:100]}{'...' if len(sql) > 100 else ''}\n"
        output += f"Rows returned: {len(rows)}\n\n"

        if columns:
            output += f"Columns: {', '.join(columns)}\n\n"

        if rows:
            output += "Sample data:\n"
            for i, row in enumerate(rows[:10]):  # Show first 10 rows
                output += f"Row {i + 1}: {row}\n"

            if len(rows) > 10:
                output += f"... and {len(rows) - 10} more rows\n"
        else:
            output += "No data returned.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_query_sql_tool: {e}")
        return f"Error: {str(e)}"


async def looker_get_looks_tool(project_id: str, folder_id: Optional[str] = None) -> str:
    """
    Get all Looks (saved queries) in Looker.

    Args:
        project_id: Project ID for credential lookup
        folder_id: Optional folder ID to filter Looks

    Returns:
        List of Looks formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.get_looks(folder_id)

        if "error" in result:
            return f"Error getting looks: {result['error']}"

        looks = result.get('looks', [])

        output = f"Looker Looks: {len(looks)} found\n"
        if folder_id:
            output += f"Folder ID: {folder_id}\n"
        output += "\n"

        if looks:
            for look in looks:
                look_id = look.get('id', 'Unknown')
                title = look.get('title', 'Unknown')
                model = look.get('model', 'Unknown')
                explore = look.get('explore', 'Unknown')
                output += f"- [{look_id}] {title} (Model: {model}, Explore: {explore})\n"
        else:
            output += "No looks found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_get_looks_tool: {e}")
        return f"Error: {str(e)}"


async def looker_run_look_tool(project_id: str, look_id: str, limit: int = 100) -> str:
    """
    Run a specific Look and get its results.

    Args:
        project_id: Project ID for credential lookup
        look_id: ID of the Look to run
        limit: Maximum number of rows to return

    Returns:
        Look results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.run_look(look_id, limit)

        if "error" in result:
            return f"Error running look: {result['error']}"

        rows = result.get('rows', [])
        columns = result.get('columns', [])
        look_info = result.get('look_info', {})

        output = f"Look Results\n"
        output += f"Look ID: {look_id}\n"
        output += f"Title: {look_info.get('title', 'Unknown')}\n"
        output += f"Model: {look_info.get('model', 'Unknown')}\n"
        output += f"Explore: {look_info.get('explore', 'Unknown')}\n"
        output += f"Rows returned: {len(rows)}\n\n"

        if columns:
            output += f"Columns: {', '.join(columns)}\n\n"

        if rows:
            output += "Sample data:\n"
            for i, row in enumerate(rows[:10]):  # Show first 10 rows
                output += f"Row {i + 1}: {row}\n"

            if len(rows) > 10:
                output += f"... and {len(rows) - 10} more rows\n"
        else:
            output += "No data returned.\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_run_look_tool: {e}")
        return f"Error: {str(e)}"


async def looker_query_url_tool(project_id: str, model_name: str, explore_name: str,
                                dimensions: List[str], measures: List[str],
                                filters: Optional[Dict[str, str]] = None) -> str:
    """
    Generate a URL for a Looker query that can be opened in the browser.

    Args:
        project_id: Project ID for credential lookup
        model_name: Name of the model
        explore_name: Name of the explore
        dimensions: List of dimension names to include
        measures: List of measure names to include
        filters: Dictionary of filters to apply

    Returns:
        URL that can be used to view the query in Looker
    """
    try:
        provider = await get_provider(project_id, "looker")
        if not provider:
            return "Error: Could not get Looker provider for project"

        result = await provider.query_url(model_name, explore_name, dimensions, measures, filters)

        if "error" in result:
            return f"Error generating query URL: {result['error']}"

        url = result.get('url', '')

        output = f"Looker Query URL\n"
        output += f"Model: {model_name}, Explore: {explore_name}\n"
        output += f"Dimensions: {', '.join(dimensions)}\n"
        output += f"Measures: {', '.join(measures)}\n"
        if filters:
            output += f"Filters: {filters}\n"
        output += f"\nURL: {url}\n"

        return output

    except Exception as e:
        logger.error(f"Error in looker_query_url_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# REDASH TOOLS
# =============================================================================

async def redash_list_queries_tool(project_id: str, page: int = 1, page_size: int = 25) -> str:
    """
    List all queries in Redash.

    Args:
        project_id: Project ID for credential lookup
        page: Page number for pagination
        page_size: Number of queries per page

    Returns:
        List of queries formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.list_queries(page, page_size)

        if "error" in result:
            return f"Error listing queries: {result['error']}"

        queries = result.get('queries', [])
        total_count = result.get('count', len(queries))

        output = f"Redash Queries (Page {page}): {len(queries)} of {total_count} total\n\n"

        if queries:
            for query in queries:
                query_id = query.get('id', 'Unknown')
                name = query.get('name', 'Untitled Query')
                created_by = query.get('user', {}).get('name', 'Unknown')
                updated_at = query.get('updated_at', 'Unknown')
                output += f"- [{query_id}] {name} (By: {created_by}, Updated: {updated_at})\n"
        else:
            output += "No queries found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_list_queries_tool: {e}")
        return f"Error: {str(e)}"


async def redash_get_query_tool(project_id: str, query_id: str) -> str:
    """
    Get details of a specific Redash query.

    Args:
        project_id: Project ID for credential lookup
        query_id: ID of the query to retrieve

    Returns:
        Query details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.get_query(query_id)

        if "error" in result:
            return f"Error getting query: {result['error']}"

        query = result.get('query', {})

        output = f"Redash Query Details\n"
        output += f"ID: {query.get('id', 'Unknown')}\n"
        output += f"Name: {query.get('name', 'Unknown')}\n"
        output += f"Description: {query.get('description', 'No description')}\n"
        output += f"Data Source: {query.get('data_source_id', 'Unknown')}\n"
        output += f"Created By: {query.get('user', {}).get('name', 'Unknown')}\n"
        output += f"Created At: {query.get('created_at', 'Unknown')}\n"
        output += f"Updated At: {query.get('updated_at', 'Unknown')}\n"
        output += f"Tags: {', '.join(query.get('tags', []))}\n\n"

        query_text = query.get('query', '')
        if query_text:
            output += f"Query:\n{query_text}\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_get_query_tool: {e}")
        return f"Error: {str(e)}"


async def redash_execute_query_tool(project_id: str, query_id: str, parameters: Optional[Dict[str, Any]] = None) -> str:
    """
    Execute a Redash query and get its results.

    Args:
        project_id: Project ID for credential lookup
        query_id: ID of the query to execute
        parameters: Optional parameters for parameterized queries

    Returns:
        Query execution results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.execute_query(query_id, parameters)

        if "error" in result:
            return f"Error executing query: {result['error']}"

        job_id = result.get('job_id')
        query_result = result.get('query_result', {})

        output = f"Redash Query Execution\n"
        output += f"Query ID: {query_id}\n"
        output += f"Job ID: {job_id}\n"

        if parameters:
            output += f"Parameters: {parameters}\n"

        # If we have immediate results
        if query_result:
            rows = query_result.get('data', {}).get('rows', [])
            columns = query_result.get('data', {}).get('columns', [])

            output += f"Rows returned: {len(rows)}\n"

            if columns:
                column_names = [col.get('name', 'Unknown') for col in columns]
                output += f"Columns: {', '.join(column_names)}\n\n"

            if rows:
                output += "Sample data:\n"
                for i, row in enumerate(rows[:10]):  # Show first 10 rows
                    output += f"Row {i + 1}: {row}\n"

                if len(rows) > 10:
                    output += f"... and {len(rows) - 10} more rows\n"
            else:
                output += "No data returned.\n"
        else:
            output += "Query submitted for execution. Use job ID to check status.\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_execute_query_tool: {e}")
        return f"Error: {str(e)}"


async def redash_get_query_job_status_tool(project_id: str, job_id: str) -> str:
    """
    Get the status of a query execution job.

    Args:
        project_id: Project ID for credential lookup
        job_id: ID of the job to check

    Returns:
        Job status formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.get_query_job_status(job_id)

        if "error" in result:
            return f"Error getting job status: {result['error']}"

        job = result.get('job', {})

        output = f"Redash Query Job Status\n"
        output += f"Job ID: {job_id}\n"
        output += f"Status: {job.get('status', 'Unknown')}\n"
        output += f"Error: {job.get('error', 'None')}\n"
        output += f"Started At: {job.get('started_at', 'Unknown')}\n"
        output += f"Completed At: {job.get('completed_at', 'Not completed')}\n"

        query_result_id = job.get('query_result_id')
        if query_result_id:
            output += f"Query Result ID: {query_result_id}\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_get_query_job_status_tool: {e}")
        return f"Error: {str(e)}"


async def redash_get_query_results_tool(project_id: str, query_result_id: str) -> str:
    """
    Get the results of a completed query execution.

    Args:
        project_id: Project ID for credential lookup
        query_result_id: ID of the query result to retrieve

    Returns:
        Query results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.get_query_results(query_result_id)

        if "error" in result:
            return f"Error getting query results: {result['error']}"

        query_result = result.get('query_result', {})
        data = query_result.get('data', {})
        rows = data.get('rows', [])
        columns = data.get('columns', [])

        output = f"Redash Query Results\n"
        output += f"Query Result ID: {query_result_id}\n"
        output += f"Retrieved At: {query_result.get('retrieved_at', 'Unknown')}\n"
        output += f"Runtime: {query_result.get('runtime', 'Unknown')} seconds\n"
        output += f"Rows returned: {len(rows)}\n"

        if columns:
            column_names = [col.get('name', 'Unknown') for col in columns]
            output += f"Columns: {', '.join(column_names)}\n\n"

        if rows:
            output += "Sample data:\n"
            for i, row in enumerate(rows[:10]):  # Show first 10 rows
                output += f"Row {i + 1}: {row}\n"

            if len(rows) > 10:
                output += f"... and {len(rows) - 10} more rows\n"
        else:
            output += "No data returned.\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_get_query_results_tool: {e}")
        return f"Error: {str(e)}"


async def redash_refresh_query_tool(project_id: str, query_id: str) -> str:
    """
    Refresh a Redash query (execute with fresh data).

    Args:
        project_id: Project ID for credential lookup
        query_id: ID of the query to refresh

    Returns:
        Refresh status formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.refresh_query(query_id)

        if "error" in result:
            return f"Error refreshing query: {result['error']}"

        job = result.get('job', {})

        output = f"Redash Query Refresh\n"
        output += f"Query ID: {query_id}\n"
        output += f"Job ID: {job.get('id', 'Unknown')}\n"
        output += f"Status: {job.get('status', 'Unknown')}\n"
        output += "Query refresh initiated. Use job ID to check status.\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_refresh_query_tool: {e}")
        return f"Error: {str(e)}"


async def redash_list_dashboards_tool(project_id: str, page: int = 1, page_size: int = 25) -> str:
    """
    List all dashboards in Redash.

    Args:
        project_id: Project ID for credential lookup
        page: Page number for pagination
        page_size: Number of dashboards per page

    Returns:
        List of dashboards formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.list_dashboards(page, page_size)

        if "error" in result:
            return f"Error listing dashboards: {result['error']}"

        dashboards = result.get('dashboards', [])
        total_count = result.get('count', len(dashboards))

        output = f"Redash Dashboards (Page {page}): {len(dashboards)} of {total_count} total\n\n"

        if dashboards:
            for dashboard in dashboards:
                dashboard_id = dashboard.get('id', 'Unknown')
                name = dashboard.get('name', 'Untitled Dashboard')
                created_by = dashboard.get('user', {}).get('name', 'Unknown')
                updated_at = dashboard.get('updated_at', 'Unknown')
                widget_count = len(dashboard.get('widgets', [])) if dashboard.get('widgets', None) else 0
                output += f"- [{dashboard_id}] {name} (By: {created_by}, Widgets: {widget_count}, Updated: {updated_at})\n"
        else:
            output += "No dashboards found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_list_dashboards_tool: {e}")
        return f"Error: {str(e)}"


async def redash_get_dashboard_tool(project_id: str, dashboard_id: str) -> str:
    """
    Get details of a specific Redash dashboard.

    Args:
        project_id: Project ID for credential lookup
        dashboard_id: ID of the dashboard to retrieve

    Returns:
        Dashboard details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.get_dashboard(dashboard_id)

        if "error" in result:
            return f"Error getting dashboard: {result['error']}"

        dashboard = result.get('dashboard', {})
        widgets = dashboard.get('widgets', [])

        output = f"Redash Dashboard Details\n"
        output += f"ID: {dashboard.get('id', 'Unknown')}\n"
        output += f"Name: {dashboard.get('name', 'Unknown')}\n"
        output += f"Slug: {dashboard.get('slug', 'Unknown')}\n"
        output += f"Created By: {dashboard.get('user', {}).get('name', 'Unknown')}\n"
        output += f"Created At: {dashboard.get('created_at', 'Unknown')}\n"
        output += f"Updated At: {dashboard.get('updated_at', 'Unknown')}\n"
        output += f"Tags: {', '.join(dashboard.get('tags', []))}\n"
        output += f"Widgets: {len(widgets)}\n\n"

        if widgets:
            output += "Widget Details:\n"
            for widget in widgets:
                widget_id = widget.get('id', 'Unknown')
                widget_text = widget.get('text', '')
                visualization = widget.get('visualization', {})
                query = visualization.get('query', {})
                query_name = query.get('name', 'Unknown Query')
                output += f"- [{widget_id}] {widget_text or 'Text Widget'} (Query: {query_name})\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_get_dashboard_tool: {e}")
        return f"Error: {str(e)}"


async def redash_list_data_sources_tool(project_id: str) -> str:
    """
    List all data sources in Redash.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of data sources formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"

        result = await provider.list_data_sources()

        if "error" in result:
            return f"Error listing data sources: {result['error']}"

        data_sources = result.get('data_sources', [])

        output = f"Redash Data Sources: {len(data_sources)} found\n\n"

        if data_sources:
            for ds in data_sources:
                ds_id = ds.get('id', 'Unknown')
                name = ds.get('name', 'Unknown')
                ds_type = ds.get('type', 'Unknown')
                syntax = ds.get('syntax', 'Unknown')
                output += f"- [{ds_id}] {name} (Type: {ds_type}, Syntax: {syntax})\n"
        else:
            output += "No data sources found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in redash_list_data_sources_tool: {e}")
        return f"Error: {str(e)}"


async def redash_create_query_tool(project_id: str, data_source_id: str, name: str, 
                                 query: str, description: str = "", 
                                 schedule: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a new query in Redash.
    
    Args:
        project_id: Project ID for credential lookup
        data_source_id: ID of the data source to query against
        name: Name for the query
        query: SQL query string
        description: Optional description for the query
        schedule: Optional schedule configuration (e.g., {"interval": "3600"})
    
    Returns:
        Created query details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"
        
        result = await provider.create_query(data_source_id, name, query, description, schedule)
        
        if "error" in result:
            return f"Error creating query: {result['error']}"
        
        created_query = result.get('query', {})
        
        output = f"Redash Query Created\n"
        output += f"Query ID: {created_query.get('id', 'Unknown')}\n"
        output += f"Name: {created_query.get('name', 'Unknown')}\n"
        output += f"Data Source ID: {created_query.get('data_source_id', 'Unknown')}\n"
        output += f"Description: {created_query.get('description', 'No description')}\n"
        output += f"Created At: {created_query.get('created_at', 'Unknown')}\n"
        output += f"Query: {query[:100]}{'...' if len(query) > 100 else ''}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redash_create_query_tool: {e}")
        return f"Error: {str(e)}"


async def redash_create_visualization_tool(project_id: str, query_id: str, viz_type: str, 
                                         name: str, options: Optional[Dict[str, Any]] = None,
                                         description: str = "") -> str:
    """
    Create a visualization for a Redash query.
    
    Args:
        project_id: Project ID for credential lookup
        query_id: ID of the query to visualize
        viz_type: Type of visualization (table, line, column, area, pie, scatter, bubble, box, pivot)
        name: Name for the visualization
        options: Visualization options (chart configuration)
        description: Optional description
    
    Returns:
        Created visualization details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"
        
        result = await provider.create_visualization(query_id, viz_type, name, options, description)
        
        if "error" in result:
            return f"Error creating visualization: {result['error']}"
        
        viz = result.get('visualization', {})
        
        output = f"Redash Visualization Created\n"
        output += f"Visualization ID: {viz.get('id', 'Unknown')}\n"
        output += f"Name: {viz.get('name', 'Unknown')}\n"
        output += f"Type: {viz.get('type', 'Unknown')}\n"
        output += f"Query ID: {query_id}\n"
        output += f"Description: {viz.get('description', 'No description')}\n"
        output += f"Created At: {viz.get('created_at', 'Unknown')}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redash_create_visualization_tool: {e}")
        return f"Error: {str(e)}"


async def redash_create_dashboard_tool(project_id: str, name: str) -> str:
    """
    Create a new dashboard in Redash.
    
    Args:
        project_id: Project ID for credential lookup
        name: Name for the dashboard
    
    Returns:
        Created dashboard details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"
        
        result = await provider.create_dashboard(name)
        
        if "error" in result:
            return f"Error creating dashboard: {result['error']}"
        
        dashboard = result.get('dashboard', {})
        
        output = f"Redash Dashboard Created\n"
        output += f"Dashboard ID: {dashboard.get('id', 'Unknown')}\n"
        output += f"Name: {dashboard.get('name', 'Unknown')}\n"
        output += f"Slug: {dashboard.get('slug', 'Unknown')}\n"
        output += f"Created At: {dashboard.get('created_at', 'Unknown')}\n"
        output += f"Is Draft: {dashboard.get('is_draft', True)}\n"
        
        # Construct dashboard URL
        dashboard_id = dashboard.get('id')
        if dashboard_id:
            output += f"Dashboard URL: /dashboards/{dashboard_id}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redash_create_dashboard_tool: {e}")
        return f"Error: {str(e)}"


async def redash_add_widget_tool(project_id: str, dashboard_id: str,
                               visualization_id: Optional[str] = None,
                               text: Optional[str] = None,
                               full_width: bool = False) -> str:
    """
    Add a widget (visualization or text) to a Redash dashboard.
    
    Args:
        project_id: Project ID for credential lookup
        dashboard_id: ID of the dashboard to add widget to
        visualization_id: ID of visualization to add (for chart widgets)
        text: Text content (for text widgets)
        full_width: Whether widget should span full width
    
    Returns:
        Added widget details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"
        
        result = await provider.add_widget(dashboard_id, visualization_id, text, full_width)
        
        if "error" in result:
            return f"Error adding widget: {result['error']}"
        
        widget = result.get('widget', {})
        
        output = f"Redash Widget Added\n"
        output += f"Widget ID: {widget.get('id', 'Unknown')}\n"
        output += f"Dashboard ID: {dashboard_id}\n"
        
        if visualization_id:
            output += f"Visualization ID: {visualization_id}\n"
            output += f"Widget Type: Visualization\n"
        elif text:
            output += f"Widget Type: Text\n"
            output += f"Text Content: {text[:100]}{'...' if len(text) > 100 else ''}\n"
        
        output += f"Full Width: {full_width}\n"
        output += f"Created At: {widget.get('created_at', 'Unknown')}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error in redash_add_widget_tool: {e}")
        return f"Error: {str(e)}"


async def redash_publish_dashboard_tool(project_id: str, dashboard_id: str) -> str:
    """
    Publish a Redash dashboard to make it accessible.
    
    Args:
        project_id: Project ID for credential lookup
        dashboard_id: ID of the dashboard to publish
    
    Returns:
        Published dashboard status formatted as a string
    """
    try:
        provider = await get_provider(project_id, "redash")
        if not provider:
            return "Error: Could not get Redash provider for project"
        
        result = await provider.publish_dashboard(dashboard_id)
        
        if "error" in result:
            return f"Error publishing dashboard: {result['error']}"
        
        dashboard = result.get('dashboard', {})
        
        output = f"Redash Dashboard Published\n"
        output += f"Dashboard ID: {dashboard.get('id', 'Unknown')}\n"
        output += f"Name: {dashboard.get('name', 'Unknown')}\n"
        output += f"Is Draft: {dashboard.get('is_draft', True)}\n"
        output += f"Updated At: {dashboard.get('updated_at', 'Unknown')}\n"
        
        # Construct dashboard URL
        dashboard_id_val = dashboard.get('id')
        if dashboard_id_val:
            output += f"Dashboard URL: /dashboards/{dashboard_id_val}\n"
        
        return output

    except Exception as e:
        logger.error(f"Error in redash_publish_dashboard_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# DATAZONE TOOLS
# =============================================================================

async def datazone_list_domains_tool(project_id: str, max_results: int = 25) -> str:
    """
    List all AWS DataZone domains.

    Args:
        project_id: Project ID for credential lookup
        max_results: Maximum number of results to return (default: 50)

    Returns:
        List of DataZone domains formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.list_domains(max_results=max_results)

        if "error" in result:
            return f"Error listing domains: {result['error']}"

        domains = result.get('domains', [])
        total_count = result.get('count', 0)

        output = f"DataZone Domains: {total_count} found\n\n"

        for domain in domains:
            output += f"Domain ID: {domain.get('id', 'Unknown')}\n"
            output += f"Name: {domain.get('name', 'Unknown')}\n"
            output += f"ARN: {domain.get('arn', 'Unknown')}\n"
            output += f"Status: {domain.get('status', 'Unknown')}\n"
            output += f"Created At: {domain.get('createdAt', 'Unknown')}\n"
            output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_list_domains_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_domain_tool(project_id: str, domain_id: str) -> str:
    """
    Get details of a specific DataZone domain.

    Args:
        project_id: Project ID for credential lookup
        domain_id: ID of the domain to retrieve

    Returns:
        Domain details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_domain(domain_id)

        if "error" in result:
            return f"Error getting domain: {result['error']}"

        domain = result.get('domain', {})

        output = f"DataZone Domain Details\n"
        output += f"Domain ID: {domain.get('id', 'Unknown')}\n"
        output += f"Name: {domain.get('name', 'Unknown')}\n"
        output += f"ARN: {domain.get('arn', 'Unknown')}\n"
        output += f"Status: {domain.get('status', 'Unknown')}\n"
        output += f"Description: {domain.get('description', 'N/A')}\n"
        output += f"Created At: {domain.get('createdAt', 'Unknown')}\n"
        output += f"Last Updated At: {domain.get('lastUpdatedAt', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_domain_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_list_projects_tool(project_id: str, domain_id: str, max_results: int = 25) -> str:
    """
    List all projects in a DataZone domain.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        max_results: Maximum number of results to return (default: 50)

    Returns:
        List of DataZone projects formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.list_projects(domain_id, max_results=max_results)

        if "error" in result:
            return f"Error listing projects: {result['error']}"

        projects = result.get('projects', [])
        total_count = result.get('count', 0)

        output = f"DataZone Projects in Domain {domain_id}: {total_count} found\n\n"

        for project in projects:
            output += f"Project ID: {project.get('id', 'Unknown')}\n"
            output += f"Name: {project.get('name', 'Unknown')}\n"
            output += f"Description: {project.get('description', 'N/A')}\n"
            output += f"Created At: {project.get('createdAt', 'Unknown')}\n"
            output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_list_projects_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_project_tool(project_id: str, domain_id: str, datazone_project_id: str) -> str:
    """
    Get details of a specific DataZone project.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        datazone_project_id: DataZone project ID to retrieve

    Returns:
        Project details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_project(domain_id, datazone_project_id)

        if "error" in result:
            return f"Error getting project: {result['error']}"

        project = result.get('project', {})

        output = f"DataZone Project Details\n"
        output += f"Project ID: {project.get('id', 'Unknown')}\n"
        output += f"Name: {project.get('name', 'Unknown')}\n"
        output += f"Domain ID: {project.get('domainId', 'Unknown')}\n"
        output += f"Description: {project.get('description', 'N/A')}\n"
        output += f"Created At: {project.get('createdAt', 'Unknown')}\n"
        output += f"Created By: {project.get('createdBy', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_project_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_search_listings_tool(project_id: str, domain_id: str,
                                       search_text: str = "", max_results: int = 25) -> str:
    """
    Search for data assets in DataZone catalog.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        search_text: Text to search for (optional)
        max_results: Maximum number of results to return (default: 50)

    Returns:
        List of data asset listings formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.search_listings(domain_id, search_text=search_text, max_results=max_results)

        if "error" in result:
            return f"Error searching listings: {result['error']}"

        listings = result.get('listings', [])
        total_count = result.get('count', 0)

        search_info = f" matching '{search_text}'" if search_text else ""
        output = f"DataZone Data Listings{search_info}: {total_count} found\n\n"

        for listing in listings:
            output += f"Listing ID: {listing.get('id', 'Unknown')}\n"
            output += f"Name: {listing.get('name', 'Unknown')}\n"
            output += f"Description: {listing.get('description', 'N/A')}\n"
            output += f"Created At: {listing.get('createdAt', 'Unknown')}\n"
            output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_search_listings_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_listing_tool(project_id: str, domain_id: str, listing_id: str) -> str:
    """
    Get details of a specific data listing.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        listing_id: Listing ID to retrieve

    Returns:
        Listing details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_listing(domain_id, listing_id)

        if "error" in result:
            return f"Error getting listing: {result['error']}"

        listing = result.get('listing', {})

        output = f"DataZone Listing Details\n"
        output += f"Listing ID: {listing.get('id', 'Unknown')}\n"
        output += f"Name: {listing.get('name', 'Unknown')}\n"
        output += f"Description: {listing.get('description', 'N/A')}\n"
        output += f"Created At: {listing.get('createdAt', 'Unknown')}\n"
        output += f"Updated At: {listing.get('updatedAt', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_listing_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_list_environments_tool(project_id: str, domain_id: str,
                                         datazone_project_id: str, max_results: int = 25) -> str:
    """
    List environments in a DataZone project.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        datazone_project_id: DataZone project ID
        max_results: Maximum number of results to return (default: 50)

    Returns:
        List of environments formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.list_environments(domain_id, datazone_project_id, max_results=max_results)

        if "error" in result:
            return f"Error listing environments: {result['error']}"

        environments = result.get('environments', [])
        total_count = result.get('count', 0)

        output = f"DataZone Environments in Project {datazone_project_id}: {total_count} found\n\n"

        for env in environments:
            output += f"Environment ID: {env.get('id', 'Unknown')}\n"
            output += f"Name: {env.get('name', 'Unknown')}\n"
            output += f"Status: {env.get('status', 'Unknown')}\n"
            output += f"Created At: {env.get('createdAt', 'Unknown')}\n"
            output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_list_environments_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_environment_tool(project_id: str, domain_id: str, environment_id: str) -> str:
    """
    Get details of a specific environment.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        environment_id: Environment ID to retrieve

    Returns:
        Environment details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_environment(domain_id, environment_id)

        if "error" in result:
            return f"Error getting environment: {result['error']}"

        env = result.get('environment', {})

        output = f"DataZone Environment Details\n"
        output += f"Environment ID: {env.get('id', 'Unknown')}\n"
        output += f"Name: {env.get('name', 'Unknown')}\n"
        output += f"Status: {env.get('status', 'Unknown')}\n"
        output += f"Description: {env.get('description', 'N/A')}\n"
        output += f"Created At: {env.get('createdAt', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_environment_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_asset_tool(project_id: str, domain_id: str, asset_id: str) -> str:
    """
    Get details of a specific data asset.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        asset_id: Asset ID to retrieve

    Returns:
        Asset details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_asset(domain_id, asset_id)

        if "error" in result:
            return f"Error getting asset: {result['error']}"

        asset = result.get('asset', {})

        output = f"DataZone Asset Details\n"
        output += f"Asset ID: {asset.get('id', 'Unknown')}\n"
        output += f"Name: {asset.get('name', 'Unknown')}\n"
        output += f"Type: {asset.get('type', 'Unknown')}\n"
        output += f"Description: {asset.get('description', 'N/A')}\n"
        output += f"Created At: {asset.get('createdAt', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_asset_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_list_asset_revisions_tool(project_id: str, domain_id: str,
                                             asset_id: str, max_results: int = 25) -> str:
    """
    List revisions of a data asset.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        asset_id: Asset ID
        max_results: Maximum number of results to return (default: 50)

    Returns:
        List of asset revisions formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.list_asset_revisions(domain_id, asset_id, max_results=max_results)

        if "error" in result:
            return f"Error listing asset revisions: {result['error']}"

        revisions = result.get('revisions', [])
        total_count = result.get('count', 0)

        output = f"DataZone Asset Revisions for Asset {asset_id}: {total_count} found\n\n"

        for revision in revisions:
            output += f"Revision: {revision.get('revision', 'Unknown')}\n"
            output += f"Created At: {revision.get('createdAt', 'Unknown')}\n"
            output += f"Created By: {revision.get('createdBy', 'Unknown')}\n"
            output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_list_asset_revisions_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_glossary_tool(project_id: str, domain_id: str, glossary_id: str) -> str:
    """
    Get details of a business glossary.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        glossary_id: Glossary ID to retrieve

    Returns:
        Glossary details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_glossary(domain_id, glossary_id)

        if "error" in result:
            return f"Error getting glossary: {result['error']}"

        glossary = result.get('glossary', {})

        output = f"DataZone Glossary Details\n"
        output += f"Glossary ID: {glossary.get('id', 'Unknown')}\n"
        output += f"Name: {glossary.get('name', 'Unknown')}\n"
        output += f"Description: {glossary.get('description', 'N/A')}\n"
        output += f"Status: {glossary.get('status', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_glossary_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_glossary_term_tool(project_id: str, domain_id: str, term_id: str) -> str:
    """
    Get details of a glossary term.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        term_id: Glossary term ID to retrieve

    Returns:
        Glossary term details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_glossary_term(domain_id, term_id)

        if "error" in result:
            return f"Error getting glossary term: {result['error']}"

        term = result.get('term', {})

        output = f"DataZone Glossary Term Details\n"
        output += f"Term ID: {term.get('id', 'Unknown')}\n"
        output += f"Name: {term.get('name', 'Unknown')}\n"
        output += f"Short Description: {term.get('shortDescription', 'N/A')}\n"
        output += f"Long Description: {term.get('longDescription', 'N/A')}\n"
        output += f"Status: {term.get('status', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_glossary_term_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_create_form_type_tool(project_id: str, domain_id: str, name: str,
                                        model: str, owning_project_id: str,
                                        description: str = "", status: str = "ENABLED") -> str:
    """
    Create a new form type in DataZone.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        name: Name of the form type
        model: JSON string representing the form model structure
        owning_project_id: DataZone project ID that will own this form type
        description: Description of the form type (optional)
        status: Status of the form type (default: ENABLED)

    Returns:
        Created form type details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        # Parse model JSON string
        import json
        try:
            model_dict = json.loads(model)
        except json.JSONDecodeError as e:
            return f"Error: Invalid model JSON format: {str(e)}"

        result = await provider.create_form_type(
            domain_id=domain_id,
            name=name,
            model=model_dict,
            owning_project_id=owning_project_id,
            description=description if description else None,
            status=status
        )

        if "error" in result:
            return f"Error creating form type: {result['error']}"

        form_type = result.get('form_type', {})

        output = f"DataZone Form Type Created Successfully\n"
        output += f"Form Type ID: {form_type.get('name', 'Unknown')}\n"
        output += f"Revision: {form_type.get('revision', 'Unknown')}\n"
        output += f"Status: {form_type.get('status', 'Unknown')}\n"
        output += f"Domain ID: {form_type.get('domainId', 'Unknown')}\n"
        output += f"Owning Project ID: {form_type.get('owningProjectId', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_create_form_type_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_form_type_tool(project_id: str, domain_id: str,
                                     form_type_id: str, revision: str = "") -> str:
    """
    Get details of a specific form type.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        form_type_id: Form type identifier
        revision: Specific revision to retrieve (optional)

    Returns:
        Form type details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_form_type(
            domain_id=domain_id,
            form_type_id=form_type_id,
            revision=revision if revision else None
        )

        if "error" in result:
            return f"Error getting form type: {result['error']}"

        form_type = result.get('form_type', {})

        output = f"DataZone Form Type Details\n"
        output += f"Name: {form_type.get('name', 'Unknown')}\n"
        output += f"Revision: {form_type.get('revision', 'Unknown')}\n"
        output += f"Status: {form_type.get('status', 'Unknown')}\n"
        output += f"Description: {form_type.get('description', 'N/A')}\n"
        output += f"Domain ID: {form_type.get('domainId', 'Unknown')}\n"
        output += f"Owning Project ID: {form_type.get('owningProjectId', 'Unknown')}\n"
        output += f"Created At: {form_type.get('createdAt', 'Unknown')}\n"
        output += f"Created By: {form_type.get('createdBy', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_form_type_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_create_asset_type_tool(project_id: str, domain_id: str, name: str,
                                         owning_project_id: str, description: str = "",
                                         forms_input: str = "") -> str:
    """
    Create a new asset type in DataZone.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        name: Name of the asset type
        owning_project_id: DataZone project ID that will own this asset type
        description: Description of the asset type (optional)
        forms_input: JSON string representing forms configuration (optional)

    Returns:
        Created asset type details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        # Parse forms_input JSON string if provided
        forms_dict = None
        if forms_input:
            import json
            try:
                forms_dict = json.loads(forms_input)
            except json.JSONDecodeError as e:
                return f"Error: Invalid forms_input JSON format: {str(e)}"

        result = await provider.create_asset_type(
            domain_id=domain_id,
            name=name,
            owning_project_id=owning_project_id,
            description=description if description else None,
            forms_input=forms_dict
        )

        if "error" in result:
            return f"Error creating asset type: {result['error']}"

        asset_type = result.get('asset_type', {})

        output = f"DataZone Asset Type Created Successfully\n"
        output += f"Asset Type ID: {asset_type.get('name', 'Unknown')}\n"
        output += f"Revision: {asset_type.get('revision', 'Unknown')}\n"
        output += f"Domain ID: {asset_type.get('domainId', 'Unknown')}\n"
        output += f"Owning Project ID: {asset_type.get('owningProjectId', 'Unknown')}\n"
        output += f"Created At: {asset_type.get('createdAt', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_create_asset_type_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_get_asset_type_tool(project_id: str, domain_id: str,
                                      asset_type_id: str, revision: str = "") -> str:
    """
    Get details of a specific asset type.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        asset_type_id: Asset type identifier
        revision: Specific revision to retrieve (optional)

    Returns:
        Asset type details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.get_asset_type(
            domain_id=domain_id,
            asset_type_id=asset_type_id,
            revision=revision if revision else None
        )

        if "error" in result:
            return f"Error getting asset type: {result['error']}"

        asset_type = result.get('asset_type', {})

        output = f"DataZone Asset Type Details\n"
        output += f"Name: {asset_type.get('name', 'Unknown')}\n"
        output += f"Revision: {asset_type.get('revision', 'Unknown')}\n"
        output += f"Description: {asset_type.get('description', 'N/A')}\n"
        output += f"Domain ID: {asset_type.get('domainId', 'Unknown')}\n"
        output += f"Owning Project ID: {asset_type.get('owningProjectId', 'Unknown')}\n"
        output += f"Created At: {asset_type.get('createdAt', 'Unknown')}\n"
        output += f"Created By: {asset_type.get('createdBy', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_get_asset_type_tool: {e}")
        return f"Error: {str(e)}"


async def datazone_list_asset_types_tool(project_id: str, domain_id: str,
                                        owning_project_id: str = "",
                                        max_results: int = 25) -> str:
    """
    List asset types in a DataZone domain.

    Args:
        project_id: Project ID for credential lookup
        domain_id: DataZone domain ID
        owning_project_id: Filter by owning project ID (optional)
        max_results: Maximum number of results to return (default: 25)

    Returns:
        List of asset types formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datazone")
        if not provider:
            return "Error: Could not get DataZone provider for project"

        result = await provider.list_asset_types(
            domain_id=domain_id,
            owning_project_id=owning_project_id if owning_project_id else None,
            max_results=max_results
        )

        if "error" in result:
            return f"Error listing asset types: {result['error']}"

        asset_types = result.get('asset_types', [])
        total_count = result.get('count', 0)

        output = f"DataZone Asset Types in Domain {domain_id}: {total_count} found\n\n"

        for asset_type in asset_types:
            output += f"Name: {asset_type.get('name', 'Unknown')}\n"
            output += f"Revision: {asset_type.get('revision', 'Unknown')}\n"
            output += f"Description: {asset_type.get('description', 'N/A')}\n"
            output += f"Owning Project ID: {asset_type.get('owningProjectId', 'Unknown')}\n"
            output += f"Created At: {asset_type.get('createdAt', 'Unknown')}\n"
            output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in datazone_list_asset_types_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# S3 TOOLS
# =============================================================================

async def s3_list_buckets_tool(project_id: str) -> str:
    """
    List all S3 buckets.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of S3 buckets formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        result = await provider.list_buckets()

        if "error" in result:
            return f"Error listing buckets: {result['error']}"

        buckets = result.get('buckets', [])
        total_count = result.get('count', 0)

        output = f"S3 Buckets: {total_count} found\n\n"

        for bucket in buckets:
            output += f"Bucket Name: {bucket.get('Name', 'Unknown')}\n"
            output += f"Creation Date: {bucket.get('CreationDate', 'Unknown')}\n"
            output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_list_buckets_tool: {e}")
        return f"Error: {str(e)}"


async def s3_list_objects_tool(project_id: str, bucket_name: str, prefix: str = "",
                               max_keys: int = 1000, delimiter: str = "") -> str:
    """
    List objects in an S3 bucket.

    Args:
        project_id: Project ID for credential lookup
        bucket_name: Name of the S3 bucket
        prefix: Prefix to filter objects (optional)
        max_keys: Maximum number of objects to return (default: 1000)
        delimiter: Delimiter for grouping keys (optional, e.g., '/' for folder structure)

    Returns:
        List of S3 objects formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        result = await provider.list_objects(
            bucket_name=bucket_name,
            prefix=prefix,
            max_keys=max_keys,
            delimiter=delimiter
        )

        if "error" in result:
            return f"Error listing objects: {result['error']}"

        objects = result.get('objects', [])
        total_count = result.get('count', 0)
        common_prefixes = result.get('common_prefixes', [])
        is_truncated = result.get('is_truncated', False)

        output = f"S3 Objects in bucket '{bucket_name}': {total_count} found\n"
        if prefix:
            output += f"Prefix: {prefix}\n"
        if is_truncated:
            output += "Note: Results are truncated. Use pagination for more results.\n"
        output += "\n"

        if common_prefixes:
            output += "Common Prefixes (Folders):\n"
            for cp in common_prefixes:
                output += f"  - {cp.get('Prefix', 'Unknown')}\n"
            output += "\n"

        if objects:
            output += "Objects:\n"
            for obj in objects:
                output += f"Key: {obj.get('Key', 'Unknown')}\n"
                output += f"  Size: {obj.get('Size', 0)} bytes\n"
                output += f"  Last Modified: {obj.get('LastModified', 'Unknown')}\n"
                output += f"  Storage Class: {obj.get('StorageClass', 'Unknown')}\n"
                output += "-" * 50 + "\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_list_objects_tool: {e}")
        return f"Error: {str(e)}"


async def s3_get_object_tool(project_id: str, bucket_name: str, object_key: str) -> str:
    """
    Get an object from S3.

    Args:
        project_id: Project ID for credential lookup
        bucket_name: Name of the S3 bucket
        object_key: Key of the object to retrieve

    Returns:
        Object content and metadata formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        result = await provider.get_object(bucket_name=bucket_name, object_key=object_key)

        if "error" in result:
            return f"Error getting object: {result['error']}"

        content = result.get('content', '')
        content_type = result.get('content_type', 'text')
        metadata = result.get('metadata', {})

        output = f"S3 Object: s3://{bucket_name}/{object_key}\n\n"
        output += "Metadata:\n"
        output += f"  Content Type: {metadata.get('content_type', 'Unknown')}\n"
        output += f"  Content Length: {metadata.get('content_length', 0)} bytes\n"
        output += f"  Last Modified: {metadata.get('last_modified', 'Unknown')}\n"
        output += f"  ETag: {metadata.get('etag', 'Unknown')}\n"
        if metadata.get('version_id'):
            output += f"  Version ID: {metadata.get('version_id')}\n"
        output += "\n"

        if content_type == 'base64':
            output += "Content (base64 encoded):\n"
            output += f"{content[:500]}...\n" if len(content) > 500 else f"{content}\n"
            output += "\nNote: Content is binary and has been base64 encoded.\n"
        else:
            output += "Content:\n"
            output += f"{content}\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_get_object_tool: {e}")
        return f"Error: {str(e)}"


async def s3_get_object_metadata_tool(project_id: str, bucket_name: str, object_key: str) -> str:
    """
    Get metadata for an S3 object without downloading the content.

    Args:
        project_id: Project ID for credential lookup
        bucket_name: Name of the S3 bucket
        object_key: Key of the object

    Returns:
        Object metadata formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        result = await provider.get_object_metadata(bucket_name=bucket_name, object_key=object_key)

        if "error" in result:
            return f"Error getting object metadata: {result['error']}"

        metadata = result.get('metadata', {})

        output = f"S3 Object Metadata: s3://{bucket_name}/{object_key}\n\n"
        output += f"Content Type: {metadata.get('content_type', 'Unknown')}\n"
        output += f"Content Length: {metadata.get('content_length', 0)} bytes\n"
        output += f"Last Modified: {metadata.get('last_modified', 'Unknown')}\n"
        output += f"ETag: {metadata.get('etag', 'Unknown')}\n"
        output += f"Storage Class: {metadata.get('storage_class', 'Unknown')}\n"
        if metadata.get('version_id'):
            output += f"Version ID: {metadata.get('version_id')}\n"
        if metadata.get('server_side_encryption'):
            output += f"Server Side Encryption: {metadata.get('server_side_encryption')}\n"

        user_metadata = metadata.get('user_metadata', {})
        if user_metadata:
            output += "\nUser Metadata:\n"
            for key, value in user_metadata.items():
                output += f"  {key}: {value}\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_get_object_metadata_tool: {e}")
        return f"Error: {str(e)}"


async def s3_create_bucket_tool(project_id: str, bucket_name: str, region: str = "") -> str:
    """
    Create a new S3 bucket.

    Args:
        project_id: Project ID for credential lookup
        bucket_name: Name of the bucket to create
        region: AWS region for the bucket (optional, defaults to provider region)

    Returns:
        Bucket creation result formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        result = await provider.create_bucket(
            bucket_name=bucket_name,
            region=region if region else None
        )

        if "error" in result:
            return f"Error creating bucket: {result['error']}"

        output = f"S3 Bucket Created Successfully\n\n"
        output += f"Bucket Name: {result.get('bucket_name', 'Unknown')}\n"
        output += f"Location: {result.get('location', 'Unknown')}\n"
        output += f"Region: {result.get('region', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_create_bucket_tool: {e}")
        return f"Error: {str(e)}"


async def s3_put_object_tool(project_id: str, bucket_name: str, object_key: str,
                             content: str, content_type: str = "",
                             storage_class: str = "STANDARD") -> str:
    """
    Upload an object to S3.

    Args:
        project_id: Project ID for credential lookup
        bucket_name: Name of the S3 bucket
        object_key: Key for the object
        content: Content to upload (text or base64 encoded)
        content_type: MIME type of the content (optional)
        storage_class: Storage class (default: STANDARD)

    Returns:
        Upload result formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        result = await provider.put_object(
            bucket_name=bucket_name,
            object_key=object_key,
            content=content,
            content_type=content_type if content_type else None,
            storage_class=storage_class
        )

        if "error" in result:
            return f"Error uploading object: {result['error']}"

        output = f"S3 Object Uploaded Successfully\n\n"
        output += f"Bucket: {result.get('bucket_name', 'Unknown')}\n"
        output += f"Key: {result.get('object_key', 'Unknown')}\n"
        output += f"ETag: {result.get('etag', 'Unknown')}\n"
        if result.get('version_id'):
            output += f"Version ID: {result.get('version_id')}\n"
        if result.get('server_side_encryption'):
            output += f"Server Side Encryption: {result.get('server_side_encryption')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_put_object_tool: {e}")
        return f"Error: {str(e)}"

async def s3_generate_presigned_url_tool(project_id: str, bucket_name: str, object_key: str,
                                         operation: str = "get_object", expiration: int = 3600,
                                         http_method: str = "") -> str:
    """
    Generate a presigned URL for S3 object operations.
    Args:
        project_id: Project ID for credential lookup
        bucket_name: Name of the S3 bucket
        object_key: Key of the object
        operation: S3 operation (get_object, put_object, delete_object)
        expiration: URL expiration time in seconds (default: 3600)
        http_method: HTTP method override (GET, PUT, DELETE)
    Returns:
        Presigned URL formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        http_method_val = http_method if http_method else None
        result = await provider.generate_presigned_url(
            bucket_name, object_key, operation=operation,
            expiration=expiration, http_method=http_method_val
        )

        if "error" in result:
            return f"Error generating presigned URL: {result['error']}"

        output = f"S3 Presigned URL Generated\n"
        output += f"URL: {result.get('url', 'N/A')}\n"
        output += f"Bucket: {result.get('bucket_name', 'N/A')}\n"
        output += f"Object Key: {result.get('object_key', 'N/A')}\n"
        output += f"Operation: {result.get('operation', 'N/A')}\n"
        output += f"Expires In: {result.get('expiration_seconds', 'N/A')} seconds\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_generate_presigned_url_tool: {e}")
        return f"Error: {str(e)}"

async def s3_generate_presigned_post_tool(project_id: str, bucket_name: str, object_key: str,
                                          expiration: int = 3600) -> str:
    """
    Generate presigned POST data for direct browser uploads to S3.
    Args:
        project_id: Project ID for credential lookup
        bucket_name: Name of the S3 bucket
        object_key: Key for the object to be uploaded
        expiration: POST policy expiration time in seconds (default: 3600)
    Returns:
        Presigned POST data formatted as a string
    """
    try:
        provider = await get_provider(project_id, "s3")
        if not provider:
            return "Error: Could not get S3 provider for project"

        result = await provider.generate_presigned_post(
            bucket_name, object_key, expiration=expiration
        )

        if "error" in result:
            return f"Error generating presigned POST: {result['error']}"

        output = f"S3 Presigned POST Data Generated\n"
        output += f"URL: {result.get('url', 'N/A')}\n"
        output += f"Bucket: {result.get('bucket_name', 'N/A')}\n"
        output += f"Object Key: {result.get('object_key', 'N/A')}\n"
        output += f"Expires In: {result.get('expiration_seconds', 'N/A')} seconds\n\n"
        output += f"Form Fields:\n"

        fields = result.get('fields', {})
        for key, value in fields.items():
            output += f"  {key}: {value}\n"

        return output

    except Exception as e:
        logger.error(f"Error in s3_generate_presigned_post_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# AZURE BLOB STORAGE TOOLS
# =============================================================================

async def azure_blob_list_containers_tool(project_id: str, max_results: int = 100) -> str:
    """
    List all containers in the Azure Blob Storage account.

    Args:
        project_id: Project ID for credential lookup
        max_results: Maximum number of containers to return (default: 100)

    Returns:
        List of containers formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.list_containers(max_results=max_results)

        if "error" in result:
            return f"Error listing containers: {result['error']}"

        containers = result.get('containers', [])
        storage_account = result.get('storage_account', 'Unknown')

        output = f"Azure Blob Storage Containers ({storage_account}): {len(containers)} found\n\n"

        if containers:
            for container in containers:
                name = container.get('name', 'Unknown')
                last_modified = container.get('last_modified', 'Unknown')
                public_access = container.get('public_access', 'None')
                output += f"- {name} (Last Modified: {last_modified}, Public Access: {public_access})\n"
        else:
            output += "No containers found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_blob_list_containers_tool: {e}")
        return f"Error: {str(e)}"


async def azure_blob_list_blobs_tool(project_id: str, container_name: str, prefix: str = "",
                                      max_results: int = 1000, delimiter: str = "") -> str:
    """
    List blobs in an Azure Blob Storage container.

    Args:
        project_id: Project ID for credential lookup
        container_name: Name of the container
        prefix: Prefix to filter blobs (optional)
        max_results: Maximum number of blobs to return (default: 1000)
        delimiter: Delimiter for virtual directory structure (optional, e.g., '/')

    Returns:
        List of blobs formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.list_blobs(container_name, prefix, max_results, delimiter)

        if "error" in result:
            return f"Error listing blobs: {result['error']}"

        blobs = result.get('blobs', [])
        prefixes = result.get('common_prefixes', [])

        output = f"Blobs in container '{container_name}'"
        if prefix:
            output += f" (prefix: {prefix})"
        output += f": {len(blobs)} found\n\n"

        if prefixes:
            output += "Virtual Directories:\n"
            for p in prefixes:
                output += f"  [DIR] {p.get('prefix', 'Unknown')}\n"
            output += "\n"

        if blobs:
            for blob in blobs:
                name = blob.get('name', 'Unknown')
                size = blob.get('size', 0)
                content_type = blob.get('content_type', 'Unknown')
                output += f"- {name} ({size} bytes, {content_type})\n"
        else:
            output += "No blobs found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_blob_list_blobs_tool: {e}")
        return f"Error: {str(e)}"


async def azure_blob_get_blob_tool(project_id: str, container_name: str, blob_name: str) -> str:
    """
    Get a blob from an Azure Blob Storage container.

    Args:
        project_id: Project ID for credential lookup
        container_name: Name of the container
        blob_name: Name of the blob to retrieve

    Returns:
        Blob content and metadata formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.get_blob(container_name, blob_name)

        if "error" in result:
            return f"Error getting blob: {result['error']}"

        content_type = result.get('content_type', 'text')
        content = result.get('content', '')
        metadata = result.get('metadata', {})

        output = f"Blob: {blob_name}\n"
        output += f"Content Type: {metadata.get('content_type', 'Unknown')}\n"
        output += f"Size: {metadata.get('content_length', 0)} bytes\n"
        output += f"Last Modified: {metadata.get('last_modified', 'Unknown')}\n"
        output += f"Blob Type: {metadata.get('blob_type', 'Unknown')}\n\n"

        if content_type == 'text':
            output += "Content:\n"
            output += content[:10000]  # Limit content display
            if len(content) > 10000:
                output += f"\n... (truncated, total {len(content)} characters)"
        else:
            output += f"Content: [Base64 encoded binary data, {len(content)} characters]"

        return output

    except Exception as e:
        logger.error(f"Error in azure_blob_get_blob_tool: {e}")
        return f"Error: {str(e)}"


async def azure_blob_get_blob_metadata_tool(project_id: str, container_name: str, blob_name: str) -> str:
    """
    Get metadata for a blob without downloading the content.

    Args:
        project_id: Project ID for credential lookup
        container_name: Name of the container
        blob_name: Name of the blob

    Returns:
        Blob metadata formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.get_blob_metadata(container_name, blob_name)

        if "error" in result:
            return f"Error getting blob metadata: {result['error']}"

        metadata = result.get('metadata', {})

        output = f"Blob Metadata: {blob_name}\n\n"
        for key, value in metadata.items():
            output += f"  {key}: {value}\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_blob_get_blob_metadata_tool: {e}")
        return f"Error: {str(e)}"


async def azure_blob_upload_blob_tool(project_id: str, container_name: str, blob_name: str,
                                       content: str, content_type: str = None,
                                       overwrite: bool = True) -> str:
    """
    Upload a blob to an Azure Blob Storage container.

    Args:
        project_id: Project ID for credential lookup
        container_name: Name of the container
        blob_name: Name for the blob
        content: Content to upload
        content_type: MIME type of the content (optional)
        overwrite: Whether to overwrite if blob exists (default: True)

    Returns:
        Upload result formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.upload_blob(container_name, blob_name, content, content_type, None, overwrite)

        if "error" in result:
            return f"Error uploading blob: {result['error']}"

        if result.get('success'):
            return f"Successfully uploaded blob '{blob_name}' to container '{container_name}'\nETag: {result.get('etag', 'Unknown')}"
        else:
            return f"Upload failed: {result}"

    except Exception as e:
        logger.error(f"Error in azure_blob_upload_blob_tool: {e}")
        return f"Error: {str(e)}"


async def azure_blob_delete_blob_tool(project_id: str, container_name: str, blob_name: str) -> str:
    """
    Delete a blob from an Azure Blob Storage container.

    Args:
        project_id: Project ID for credential lookup
        container_name: Name of the container
        blob_name: Name of the blob to delete

    Returns:
        Deletion result formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.delete_blob(container_name, blob_name)

        if "error" in result:
            return f"Error deleting blob: {result['error']}"

        if result.get('success'):
            return f"Successfully deleted blob '{blob_name}' from container '{container_name}'"
        else:
            return f"Deletion failed: {result}"

    except Exception as e:
        logger.error(f"Error in azure_blob_delete_blob_tool: {e}")
        return f"Error: {str(e)}"


async def azure_blob_generate_sas_url_tool(project_id: str, container_name: str, blob_name: str,
                                            expiry_hours: int = 1, permission: str = "r") -> str:
    """
    Generate a SAS (Shared Access Signature) URL for a blob.

    Args:
        project_id: Project ID for credential lookup
        container_name: Name of the container
        blob_name: Name of the blob
        expiry_hours: URL expiration time in hours (default: 1)
        permission: Permission string (r=read, w=write, d=delete, default: r)

    Returns:
        SAS URL formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.generate_sas_url(container_name, blob_name, expiry_hours, permission)

        if "error" in result:
            return f"Error generating SAS URL: {result['error']}"

        if result.get('success'):
            output = f"SAS URL for '{blob_name}':\n\n"
            output += f"URL: {result.get('url', 'Unknown')}\n"
            output += f"Expiry: {result.get('expiry', 'Unknown')}\n"
            output += f"Permission: {result.get('permission', 'Unknown')}"
            return output
        else:
            return f"SAS URL generation failed: {result}"

    except Exception as e:
        logger.error(f"Error in azure_blob_generate_sas_url_tool: {e}")
        return f"Error: {str(e)}"


async def azure_blob_get_container_properties_tool(project_id: str, container_name: str) -> str:
    """
    Get properties for a container.

    Args:
        project_id: Project ID for credential lookup
        container_name: Name of the container

    Returns:
        Container properties formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_blob_storage")
        if not provider:
            return "Error: Could not get Azure Blob Storage provider for project"

        result = await provider.get_container_properties(container_name)

        if "error" in result:
            return f"Error getting container properties: {result['error']}"

        output = f"Container Properties: {container_name}\n\n"
        for key, value in result.items():
            output += f"  {key}: {value}\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_blob_get_container_properties_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# AZURE DATA FACTORY TOOLS
# =============================================================================

async def azure_adf_list_pipelines_tool(project_id: str) -> str:
    """
    List all pipelines in the Azure Data Factory.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of pipelines formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.list_pipelines()

        if "error" in result:
            return f"Error listing pipelines: {result['error']}"

        pipelines = result.get('pipelines', [])
        factory_name = result.get('factory_name', 'Unknown')

        output = f"Azure Data Factory Pipelines ({factory_name}): {len(pipelines)} found\n\n"

        if pipelines:
            for pipeline in pipelines:
                name = pipeline.get('name', 'Unknown')
                activity_count = pipeline.get('activity_count', 0)
                folder = pipeline.get('folder', 'Root')
                description = pipeline.get('description', '')
                output += f"- {name} ({activity_count} activities, Folder: {folder})\n"
                if description:
                    output += f"    Description: {description}\n"
        else:
            output += "No pipelines found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_list_pipelines_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_pipeline_tool(project_id: str, pipeline_name: str) -> str:
    """
    Get detailed information about a specific pipeline.

    Args:
        project_id: Project ID for credential lookup
        pipeline_name: Name of the pipeline

    Returns:
        Pipeline details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_pipeline(pipeline_name)

        if "error" in result:
            return f"Error getting pipeline: {result['error']}"

        output = f"Pipeline: {result.get('name', 'Unknown')}\n\n"
        output += f"Description: {result.get('description', 'None')}\n"
        output += f"Folder: {result.get('folder', 'Root')}\n"
        output += f"Activity Count: {result.get('activity_count', 0)}\n\n"

        activities = result.get('activities', [])
        if activities:
            output += "Activities:\n"
            for activity in activities:
                output += f"  - {activity.get('name')} ({activity.get('type')})\n"
                if activity.get('depends_on'):
                    output += f"      Depends on: {', '.join(activity.get('depends_on', []))}\n"

        params = result.get('parameters', {})
        if params:
            output += "\nParameters:\n"
            for name, details in params.items():
                output += f"  - {name}: {details.get('type')} (default: {details.get('default_value')})\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_pipeline_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_run_pipeline_tool(project_id: str, pipeline_name: str,
                                       parameters: str = None) -> str:
    """
    Trigger a pipeline run.

    Args:
        project_id: Project ID for credential lookup
        pipeline_name: Name of the pipeline to run
        parameters: JSON string of parameters to pass to the pipeline (optional)

    Returns:
        Run ID and status formatted as a string
    """
    try:
        import json
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        params_dict = None
        if parameters:
            try:
                params_dict = json.loads(parameters)
            except json.JSONDecodeError as e:
                return f"Error parsing parameters JSON: {e}"

        result = await provider.run_pipeline(pipeline_name, params_dict)

        if "error" in result:
            return f"Error running pipeline: {result['error']}"

        if result.get('success'):
            return f"Pipeline '{pipeline_name}' triggered successfully\nRun ID: {result.get('run_id', 'Unknown')}"
        else:
            return f"Pipeline trigger failed: {result}"

    except Exception as e:
        logger.error(f"Error in azure_adf_run_pipeline_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_pipeline_run_tool(project_id: str, run_id: str) -> str:
    """
    Get the status of a pipeline run.

    Args:
        project_id: Project ID for credential lookup
        run_id: The run ID to check

    Returns:
        Run status and details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_pipeline_run(run_id)

        if "error" in result:
            return f"Error getting pipeline run: {result['error']}"

        output = f"Pipeline Run: {result.get('run_id', 'Unknown')}\n\n"
        output += f"Pipeline: {result.get('pipeline_name', 'Unknown')}\n"
        output += f"Status: {result.get('status', 'Unknown')}\n"
        output += f"Start: {result.get('run_start', 'Unknown')}\n"
        output += f"End: {result.get('run_end', 'Unknown')}\n"
        output += f"Duration: {result.get('duration_in_ms', 0)}ms\n"

        if result.get('message'):
            output += f"Message: {result.get('message')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_pipeline_run_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_list_pipeline_runs_tool(project_id: str, pipeline_name: str = None,
                                             days_back: int = 7, max_results: int = 100) -> str:
    """
    List recent pipeline runs.

    Args:
        project_id: Project ID for credential lookup
        pipeline_name: Optional filter by pipeline name
        days_back: Number of days to look back (default: 7)
        max_results: Maximum number of runs to return (default: 100)

    Returns:
        List of pipeline runs formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.list_pipeline_runs(pipeline_name, days_back, max_results)

        if "error" in result:
            return f"Error listing pipeline runs: {result['error']}"

        runs = result.get('runs', [])

        output = f"Pipeline Runs (last {days_back} days): {len(runs)} found\n\n"

        if runs:
            for run in runs:
                status = run.get('status', 'Unknown')
                pipeline = run.get('pipeline_name', 'Unknown')
                run_id = run.get('run_id', 'Unknown')[:8]
                start = run.get('run_start', 'Unknown')
                output += f"- [{status}] {pipeline} (ID: {run_id}..., Start: {start})\n"
        else:
            output += "No pipeline runs found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_list_pipeline_runs_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_list_datasets_tool(project_id: str) -> str:
    """
    List all datasets in the Azure Data Factory.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of datasets formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.list_datasets()

        if "error" in result:
            return f"Error listing datasets: {result['error']}"

        datasets = result.get('datasets', [])
        factory_name = result.get('factory_name', 'Unknown')

        output = f"Azure Data Factory Datasets ({factory_name}): {len(datasets)} found\n\n"

        if datasets:
            for dataset in datasets:
                name = dataset.get('name', 'Unknown')
                ds_type = dataset.get('type', 'Unknown')
                linked_service = dataset.get('linked_service_name', 'Unknown')
                output += f"- {name} (Type: {ds_type}, Linked Service: {linked_service})\n"
        else:
            output += "No datasets found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_list_datasets_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_dataset_tool(project_id: str, dataset_name: str) -> str:
    """
    Get detailed information about a specific dataset.

    Args:
        project_id: Project ID for credential lookup
        dataset_name: Name of the dataset

    Returns:
        Dataset details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_dataset(dataset_name)

        if "error" in result:
            return f"Error getting dataset: {result['error']}"

        output = f"Dataset: {result.get('name', 'Unknown')}\n\n"
        output += f"Type: {result.get('type', 'Unknown')}\n"
        output += f"Description: {result.get('description', 'None')}\n"
        output += f"Linked Service: {result.get('linked_service_name', 'Unknown')}\n"
        output += f"Folder: {result.get('folder', 'Root')}\n"

        params = result.get('parameters', {})
        if params:
            output += "\nParameters:\n"
            for name, details in params.items():
                output += f"  - {name}: {details.get('type')} (default: {details.get('default_value')})\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_dataset_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_list_triggers_tool(project_id: str) -> str:
    """
    List all triggers in the Azure Data Factory.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of triggers formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.list_triggers()

        if "error" in result:
            return f"Error listing triggers: {result['error']}"

        triggers = result.get('triggers', [])
        factory_name = result.get('factory_name', 'Unknown')

        output = f"Azure Data Factory Triggers ({factory_name}): {len(triggers)} found\n\n"

        if triggers:
            for trigger in triggers:
                name = trigger.get('name', 'Unknown')
                trig_type = trigger.get('type', 'Unknown')
                state = trigger.get('runtime_state', 'Unknown')
                output += f"- {name} (Type: {trig_type}, State: {state})\n"
        else:
            output += "No triggers found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_list_triggers_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_trigger_tool(project_id: str, trigger_name: str) -> str:
    """
    Get detailed information about a specific trigger.

    Args:
        project_id: Project ID for credential lookup
        trigger_name: Name of the trigger

    Returns:
        Trigger details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_trigger(trigger_name)

        if "error" in result:
            return f"Error getting trigger: {result['error']}"

        output = f"Trigger: {result.get('name', 'Unknown')}\n\n"
        output += f"Type: {result.get('type', 'Unknown')}\n"
        output += f"Description: {result.get('description', 'None')}\n"
        output += f"Runtime State: {result.get('runtime_state', 'Unknown')}\n"

        recurrence = result.get('recurrence')
        if recurrence:
            output += "\nSchedule:\n"
            output += f"  Frequency: {recurrence.get('frequency')}\n"
            output += f"  Interval: {recurrence.get('interval')}\n"
            output += f"  Start Time: {recurrence.get('start_time')}\n"
            output += f"  Time Zone: {recurrence.get('time_zone')}\n"

        pipelines = result.get('pipelines', [])
        if pipelines:
            output += "\nPipelines:\n"
            for p in pipelines:
                output += f"  - {p.get('pipeline_name')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_trigger_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_list_linked_services_tool(project_id: str) -> str:
    """
    List all linked services in the Azure Data Factory.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of linked services formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.list_linked_services()

        if "error" in result:
            return f"Error listing linked services: {result['error']}"

        linked_services = result.get('linked_services', [])
        factory_name = result.get('factory_name', 'Unknown')

        output = f"Azure Data Factory Linked Services ({factory_name}): {len(linked_services)} found\n\n"

        if linked_services:
            for ls in linked_services:
                name = ls.get('name', 'Unknown')
                ls_type = ls.get('type', 'Unknown')
                connect_via = ls.get('connect_via', 'Default')
                output += f"- {name} (Type: {ls_type}, IR: {connect_via})\n"
        else:
            output += "No linked services found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_list_linked_services_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_linked_service_tool(project_id: str, service_name: str) -> str:
    """
    Get detailed information about a specific linked service.

    Args:
        project_id: Project ID for credential lookup
        service_name: Name of the linked service

    Returns:
        Linked service details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_linked_service(service_name)

        if "error" in result:
            return f"Error getting linked service: {result['error']}"

        output = f"Linked Service: {result.get('name', 'Unknown')}\n\n"
        output += f"Type: {result.get('type', 'Unknown')}\n"
        output += f"Description: {result.get('description', 'None')}\n"
        output += f"Integration Runtime: {result.get('connect_via', 'Default')}\n"

        params = result.get('parameters', {})
        if params:
            output += "\nParameters:\n"
            for name, details in params.items():
                output += f"  - {name}: {details.get('type')} (default: {details.get('default_value')})\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_linked_service_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_list_data_flows_tool(project_id: str) -> str:
    """
    List all data flows in the Azure Data Factory.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of data flows formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.list_data_flows()

        if "error" in result:
            return f"Error listing data flows: {result['error']}"

        data_flows = result.get('data_flows', [])
        factory_name = result.get('factory_name', 'Unknown')

        output = f"Azure Data Factory Data Flows ({factory_name}): {len(data_flows)} found\n\n"

        if data_flows:
            for df in data_flows:
                name = df.get('name', 'Unknown')
                df_type = df.get('type', 'Unknown')
                folder = df.get('folder', 'Root')
                output += f"- {name} (Type: {df_type}, Folder: {folder})\n"
        else:
            output += "No data flows found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_list_data_flows_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_data_flow_tool(project_id: str, data_flow_name: str) -> str:
    """
    Get detailed information about a specific data flow.

    Args:
        project_id: Project ID for credential lookup
        data_flow_name: Name of the data flow

    Returns:
        Data flow details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_data_flow(data_flow_name)

        if "error" in result:
            return f"Error getting data flow: {result['error']}"

        output = f"Data Flow: {result.get('name', 'Unknown')}\n\n"
        output += f"Type: {result.get('type', 'Unknown')}\n"
        output += f"Description: {result.get('description', 'None')}\n"
        output += f"Folder: {result.get('folder', 'Root')}\n"

        sources = result.get('sources', [])
        if sources:
            output += "\nSources:\n"
            for s in sources:
                output += f"  - {s.get('name')} (Dataset: {s.get('dataset')})\n"

        sinks = result.get('sinks', [])
        if sinks:
            output += "\nSinks:\n"
            for s in sinks:
                output += f"  - {s.get('name')} (Dataset: {s.get('dataset')})\n"

        transformations = result.get('transformations', [])
        if transformations:
            output += "\nTransformations:\n"
            for t in transformations:
                output += f"  - {t.get('name')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_data_flow_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_list_integration_runtimes_tool(project_id: str) -> str:
    """
    List all integration runtimes in the Azure Data Factory.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of integration runtimes formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.list_integration_runtimes()

        if "error" in result:
            return f"Error listing integration runtimes: {result['error']}"

        runtimes = result.get('integration_runtimes', [])
        factory_name = result.get('factory_name', 'Unknown')

        output = f"Azure Data Factory Integration Runtimes ({factory_name}): {len(runtimes)} found\n\n"

        if runtimes:
            for ir in runtimes:
                name = ir.get('name', 'Unknown')
                ir_type = ir.get('type', 'Unknown')
                description = ir.get('description', '')
                output += f"- {name} (Type: {ir_type})\n"
                if description:
                    output += f"    Description: {description}\n"
        else:
            output += "No integration runtimes found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_list_integration_runtimes_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_integration_runtime_tool(project_id: str, runtime_name: str) -> str:
    """
    Get detailed information about a specific integration runtime.

    Args:
        project_id: Project ID for credential lookup
        runtime_name: Name of the integration runtime

    Returns:
        Integration runtime details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_integration_runtime(runtime_name)

        if "error" in result:
            return f"Error getting integration runtime: {result['error']}"

        output = f"Integration Runtime: {result.get('name', 'Unknown')}\n\n"
        output += f"Type: {result.get('type', 'Unknown')}\n"
        output += f"Description: {result.get('description', 'None')}\n"
        output += f"State: {result.get('state', 'Unknown')}\n"

        nodes = result.get('nodes', [])
        if nodes:
            output += "\nNodes:\n"
            for node in nodes:
                output += f"  - {node.get('node_name')} (Status: {node.get('status')}, Version: {node.get('version')})\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_integration_runtime_tool: {e}")
        return f"Error: {str(e)}"


async def azure_adf_get_factory_info_tool(project_id: str) -> str:
    """
    Get information about the Data Factory itself.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        Factory information formatted as a string
    """
    try:
        provider = await get_provider(project_id, "azure_data_factory")
        if not provider:
            return "Error: Could not get Azure Data Factory provider for project"

        result = await provider.get_factory_info()

        if "error" in result:
            return f"Error getting factory info: {result['error']}"

        output = f"Data Factory: {result.get('name', 'Unknown')}\n\n"
        output += f"Location: {result.get('location', 'Unknown')}\n"
        output += f"Provisioning State: {result.get('provisioning_state', 'Unknown')}\n"
        output += f"Create Time: {result.get('create_time', 'Unknown')}\n"
        output += f"Version: {result.get('version', 'Unknown')}\n"

        global_params = result.get('global_parameters', [])
        if global_params:
            output += f"\nGlobal Parameters: {', '.join(global_params)}\n"

        tags = result.get('tags', {})
        if tags:
            output += "\nTags:\n"
            for key, value in tags.items():
                output += f"  {key}: {value}\n"

        return output

    except Exception as e:
        logger.error(f"Error in azure_adf_get_factory_info_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# DBT CLOUD TOOLS
# =============================================================================

async def dbt_list_projects_tool(project_id: str) -> str:
    """
    List all dbt Cloud projects in the account.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of dbt Cloud projects formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.list_projects()

        if "error" in result:
            return f"Error listing projects: {result['error']}"

        projects = result.get('projects', [])

        output = f"dbt Cloud Projects: {len(projects)} found\n\n"

        if projects:
            for project in projects:
                proj_id = project.get('id', 'Unknown')
                name = project.get('name', 'Unknown')
                state = project.get('state', 'Unknown')
                repository_id = project.get('repository_id', 'None')
                output += f"- [{proj_id}] {name} (State: {state}, Repo ID: {repository_id})\n"
        else:
            output += "No projects found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_list_projects_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_list_environments_tool(project_id: str, dbt_project_id: Optional[str] = None) -> str:
    """
    List all environments in a dbt Cloud project.

    Args:
        project_id: Project ID for credential lookup
        dbt_project_id: dbt Cloud project ID (optional if configured in credentials)

    Returns:
        List of environments formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.list_environments(dbt_project_id)

        if "error" in result:
            return f"Error listing environments: {result['error']}"

        environments = result.get('environments', [])

        output = f"dbt Cloud Environments: {len(environments)} found\n\n"

        if environments:
            for env in environments:
                env_id = env.get('id', 'Unknown')
                name = env.get('name', 'Unknown')
                env_type = env.get('type', 'Unknown')
                state = env.get('state', 'Unknown')
                output += f"- [{env_id}] {name} (Type: {env_type}, State: {state})\n"
        else:
            output += "No environments found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_list_environments_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_list_jobs_tool(project_id: str, dbt_project_id: Optional[str] = None) -> str:
    """
    List all jobs in a dbt Cloud project.

    Args:
        project_id: Project ID for credential lookup
        dbt_project_id: dbt Cloud project ID (optional if configured in credentials)

    Returns:
        List of jobs formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.list_jobs(dbt_project_id)

        if "error" in result:
            return f"Error listing jobs: {result['error']}"

        jobs = result.get('jobs', [])

        output = f"dbt Cloud Jobs: {len(jobs)} found\n\n"

        if jobs:
            for job in jobs:
                job_id = job.get('id', 'Unknown')
                name = job.get('name', 'Unknown')
                state = job.get('state', 'Unknown')
                environment_id = job.get('environment_id', 'Unknown')
                output += f"- [{job_id}] {name} (State: {state}, Env ID: {environment_id})\n"
        else:
            output += "No jobs found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_list_jobs_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_trigger_job_run_tool(project_id: str, job_id: str, cause: str = "API trigger",
                                   git_sha: Optional[str] = None,
                                   schema_override: Optional[str] = None,
                                   dbt_version_override: Optional[str] = None,
                                   target_name_override: Optional[str] = None,
                                   generate_docs_override: Optional[bool] = None,
                                   timeout_seconds_override: Optional[int] = None,
                                   steps_override: Optional[List[str]] = None) -> str:
    """
    Trigger a dbt Cloud job run with optional overrides.

    Args:
        project_id: Project ID for credential lookup
        job_id: dbt Cloud job ID to trigger
        cause: Reason for triggering the job
        git_sha: Optional git SHA to run against
        schema_override: Optional schema override
        dbt_version_override: Optional dbt version override
        target_name_override: Optional target name override
        generate_docs_override: Optional docs generation override
        timeout_seconds_override: Optional timeout override
        steps_override: Optional list of steps to run

    Returns:
        Job run details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.trigger_job_run(
            job_id=job_id,
            cause=cause,
            git_sha=git_sha,
            schema_override=schema_override,
            dbt_version_override=dbt_version_override,
            target_name_override=target_name_override,
            generate_docs_override=generate_docs_override,
            timeout_seconds_override=timeout_seconds_override,
            steps_override=steps_override
        )

        if "error" in result:
            return f"Error triggering job run: {result['error']}"

        run = result.get('run', {})

        output = f"dbt Cloud Job Run Triggered\n"
        output += f"Run ID: {run.get('id', 'Unknown')}\n"
        output += f"Job ID: {job_id}\n"
        output += f"Status: {run.get('status_humanized', 'Unknown')}\n"
        output += f"Cause: {cause}\n"
        output += f"Triggered At: {run.get('created_at', 'Unknown')}\n"

        if git_sha:
            output += f"Git SHA: {git_sha}\n"
        if schema_override:
            output += f"Schema Override: {schema_override}\n"
        if steps_override:
            output += f"Steps Override: {', '.join(steps_override)}\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_trigger_job_run_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_get_job_run_tool(project_id: str, run_id: str, include_related: Optional[List[str]] = None) -> str:
    """
    Get details of a specific dbt Cloud job run.

    Args:
        project_id: Project ID for credential lookup
        run_id: Job run ID to retrieve
        include_related: Optional list of related objects to include

    Returns:
        Job run details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.get_job_run(run_id, include_related)

        if "error" in result:
            return f"Error getting job run: {result['error']}"

        run = result.get('run', {})

        output = f"dbt Cloud Job Run Details\n"
        output += f"Run ID: {run.get('id', 'Unknown')}\n"
        output += f"Job ID: {run.get('job_definition_id', 'Unknown')}\n"
        output += f"Status: {run.get('status_humanized', 'Unknown')}\n"
        output += f"Started At: {run.get('started_at', 'Unknown')}\n"
        output += f"Finished At: {run.get('finished_at', 'Unknown')}\n"
        output += f"Duration: {run.get('duration_humanized', 'Unknown')}\n"
        output += f"Git SHA: {run.get('git_sha', 'Unknown')}\n"
        output += f"Git Branch: {run.get('git_branch', 'Unknown')}\n"

        # Include run steps if available
        run_steps = run.get('run_steps', [])
        if run_steps:
            output += f"\nRun Steps ({len(run_steps)}):\n"
            for step in run_steps:
                step_name = step.get('name', 'Unknown')
                step_status = step.get('status_humanized', 'Unknown')
                output += f"- {step_name}: {step_status}\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_get_job_run_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_list_job_runs_tool(project_id: str, job_id: Optional[str] = None,
                                 status: Optional[str] = None,
                                 limit: int = 50) -> str:
    """
    List recent job runs with optional filtering.

    Args:
        project_id: Project ID for credential lookup
        job_id: Optional job ID to filter by
        status: Optional status to filter by (e.g., 'success', 'error', 'running')
        limit: Maximum number of runs to return

    Returns:
        List of job runs formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.list_job_runs(job_id=job_id, status=status, limit=limit)

        if "error" in result:
            return f"Error listing job runs: {result['error']}"

        runs = result.get('runs', [])
        total_count = result.get('total_count', len(runs))

        output = f"dbt Cloud Job Runs: {len(runs)} of {total_count} total\n"
        if job_id:
            output += f"Filtered by Job ID: {job_id}\n"
        if status:
            output += f"Filtered by Status: {status}\n"
        output += "\n"

        if runs:
            for run in runs:
                run_id = run.get('id', 'Unknown')
                job_id_val = run.get('job_definition_id', 'Unknown')
                status_val = run.get('status_humanized', 'Unknown')
                started_at = run.get('started_at', 'Unknown')
                duration = run.get('duration_humanized', 'Unknown')
                output += f"- [{run_id}] Job {job_id_val} - {status_val} (Started: {started_at}, Duration: {duration})\n"
        else:
            output += "No job runs found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_list_job_runs_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_cancel_job_run_tool(project_id: str, run_id: str) -> str:
    """
    Cancel a running dbt Cloud job.

    Args:
        project_id: Project ID for credential lookup
        run_id: Job run ID to cancel

    Returns:
        Cancellation result formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.cancel_job_run(run_id)

        if "error" in result:
            return f"Error cancelling job run: {result['error']}"

        run = result.get('run', {})

        output = f"dbt Cloud Job Run Cancellation\n"
        output += f"Run ID: {run.get('id', 'Unknown')}\n"
        output += f"Status: {run.get('status_humanized', 'Unknown')}\n"
        output += "Job run cancellation requested.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_cancel_job_run_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_list_models_tool(project_id: str, environment_id: Optional[str] = None) -> str:
    """
    List all models in a dbt project using Discovery API.

    Args:
        project_id: Project ID for credential lookup
        environment_id: dbt Cloud environment ID (optional if configured in credentials)

    Returns:
        List of models formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.list_models(environment_id)

        if "error" in result:
            return f"Error listing models: {result['error']}"

        models = result.get('models', [])

        output = f"dbt Models: {len(models)} found\n\n"

        if models:
            for model in models:
                unique_id = model.get('uniqueId', 'Unknown')
                name = model.get('name', 'Unknown')
                schema = model.get('schema', 'Unknown')
                materialized_type = model.get('materializedType', 'Unknown')
                package_name = model.get('packageName', 'Unknown')
                output += f"- {name} ({unique_id})\n"
                output += f"  Schema: {schema}, Type: {materialized_type}, Package: {package_name}\n"
        else:
            output += "No models found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_list_models_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_get_model_details_tool(project_id: str, model_unique_id: str,
                                     environment_id: Optional[str] = None) -> str:
    """
    Get detailed information about a specific dbt model.

    Args:
        project_id: Project ID for credential lookup
        model_unique_id: Unique ID of the model to retrieve
        environment_id: dbt Cloud environment ID (optional if configured in credentials)

    Returns:
        Model details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.get_model_details(model_unique_id, environment_id)

        if "error" in result:
            return f"Error getting model details: {result['error']}"

        model = result.get('model', {})

        output = f"dbt Model Details\n"
        output += f"Name: {model.get('name', 'Unknown')}\n"
        output += f"Unique ID: {model.get('uniqueId', 'Unknown')}\n"
        output += f"Schema: {model.get('schema', 'Unknown')}\n"
        output += f"Database: {model.get('database', 'Unknown')}\n"
        output += f"Materialized Type: {model.get('materializedType', 'Unknown')}\n"
        output += f"Package: {model.get('packageName', 'Unknown')}\n"
        output += f"Description: {model.get('description', 'No description')}\n"

        # Tags
        tags = model.get('tags', [])
        if tags:
            output += f"Tags: {', '.join(tags)}\n"

        # Columns
        columns = model.get('columns', [])
        if columns:
            output += f"\nColumns ({len(columns)}):\n"
            for col in columns:
                col_name = col.get('name', 'Unknown')
                col_type = col.get('type', 'Unknown')
                col_desc = col.get('description', 'No description')
                output += f"- {col_name} ({col_type}): {col_desc}\n"

        # Parents
        parents = model.get('parents', [])
        if parents:
            output += f"\nParent Dependencies ({len(parents)}):\n"
            for parent in parents:
                parent_name = parent.get('name', 'Unknown')
                parent_type = parent.get('resourceType', 'Unknown')
                output += f"- {parent_name} ({parent_type})\n"

        # Children
        children = model.get('children', [])
        if children:
            output += f"\nChild Dependencies ({len(children)}):\n"
            for child in children:
                child_name = child.get('name', 'Unknown')
                child_type = child.get('resourceType', 'Unknown')
                output += f"- {child_name} ({child_type})\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_get_model_details_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_list_metrics_tool(project_id: str, environment_id: Optional[str] = None) -> str:
    """
    List all metrics using dbt Semantic Layer API.

    Args:
        project_id: Project ID for credential lookup
        environment_id: dbt Cloud environment ID (optional if configured in credentials)

    Returns:
        List of metrics formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.list_metrics(environment_id)

        if "error" in result:
            return f"Error listing metrics: {result['error']}"

        metrics = result.get('metrics', [])

        output = f"dbt Metrics: {len(metrics)} found\n\n"

        if metrics:
            for metric in metrics:
                name = metric.get('name', 'Unknown')
                description = metric.get('description', 'No description')
                metric_type = metric.get('type', 'Unknown')
                output += f"- {name} ({metric_type})\n"
                output += f"  Description: {description}\n"
        else:
            output += "No metrics found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_list_metrics_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_query_metrics_tool(project_id: str, metrics: List[str],
                                 group_by: Optional[List[str]] = None,
                                 where: Optional[List[str]] = None,
                                 order_by: Optional[List[str]] = None,
                                 limit: Optional[int] = None,
                                 environment_id: Optional[str] = None) -> str:
    """
    Query metrics using dbt Semantic Layer API.

    Args:
        project_id: Project ID for credential lookup
        metrics: List of metric names to query
        group_by: Optional list of dimensions to group by
        where: Optional list of where clauses
        order_by: Optional list of order by clauses
        limit: Optional limit on results
        environment_id: dbt Cloud environment ID (optional if configured in credentials)

    Returns:
        Query results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.query_metrics(
            metrics=metrics,
            group_by=group_by,
            where=where,
            order_by=order_by,
            limit=limit,
            environment_id=environment_id
        )

        if "error" in result:
            return f"Error querying metrics: {result['error']}"

        query_result = result.get('query_result', {})

        output = f"dbt Metrics Query Results\n"
        output += f"Metrics: {', '.join(metrics)}\n"
        if group_by:
            output += f"Group By: {', '.join(group_by)}\n"
        if where:
            output += f"Where: {', '.join(where)}\n"
        if order_by:
            output += f"Order By: {', '.join(order_by)}\n"
        if limit:
            output += f"Limit: {limit}\n"
        output += "\n"

        # Process query results
        data = query_result.get('data', [])
        if data:
            output += f"Results ({len(data)} rows):\n"
            for i, row in enumerate(data[:10]):  # Show first 10 rows
                output += f"Row {i + 1}: {row}\n"

            if len(data) > 10:
                output += f"... and {len(data) - 10} more rows\n"
        else:
            output += "No data returned.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_query_metrics_tool: {e}")
        return f"Error: {str(e)}"


async def dbt_execute_sql_tool(project_id: str, sql: str, environment_id: Optional[str] = None) -> str:
    """
    Execute SQL using dbt Cloud SQL API.

    Args:
        project_id: Project ID for credential lookup
        sql: SQL query to execute
        environment_id: dbt Cloud environment ID (optional if configured in credentials)

    Returns:
        SQL execution results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "dbt")
        if not provider:
            return "Error: Could not get dbt Cloud provider for project"

        result = await provider.execute_sql(sql, environment_id)

        if "error" in result:
            return f"Error executing SQL: {result['error']}"

        sql_result = result.get('sql_result', {})

        output = f"dbt SQL Execution Results\n"
        output += f"Query: {sql[:100]}{'...' if len(sql) > 100 else ''}\n"

        # Process SQL results
        data = sql_result.get('data', [])
        columns = sql_result.get('columns', [])

        output += f"Rows returned: {len(data)}\n"

        if columns:
            output += f"Columns: {', '.join(columns)}\n"

        output += "\n"

        if data:
            output += "Sample data:\n"
            for i, row in enumerate(data[:10]):  # Show first 10 rows
                output += f"Row {i + 1}: {row}\n"

            if len(data) > 10:
                output += f"... and {len(data) - 10} more rows\n"
        else:
            output += "No data returned.\n"

        return output

    except Exception as e:
        logger.error(f"Error in dbt_execute_sql_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# DATAHUB TOOLS
# =============================================================================

async def datahub_search_entities_tool(project_id: str, query: str = "*", 
                                       entity_types: Optional[List[str]] = None,
                                       start: int = 0, count: int = 10) -> str:
    """
    Search for entities in DataHub.

    Args:
        project_id: Project ID for credential lookup
        query: Search query string (default: "*" for all)
        entity_types: List of entity types to filter by (DATASET, CHART, DASHBOARD, etc.)
        start: Start index for pagination
        count: Number of results per page

    Returns:
        Search results formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.search_entities(query, entity_types, start, count)

        if "error" in result:
            return f"Error searching entities: {result['error']}"

        entities = result.get('entities', [])
        total_count = result.get('total', len(entities))

        output = f"DataHub Search Results (Page {start//count + 1}): {len(entities)} of {total_count} total\n"
        output += f"Query: {query}\n"
        if entity_types:
            output += f"Entity Types: {', '.join(entity_types)}\n"
        output += "\n"

        if entities:
            for item in entities:
                entity = item.get('entity', {})
                urn = entity.get('urn', 'Unknown')
                entity_type = entity.get('type', 'Unknown')
                properties = entity.get('properties', {})
                name = properties.get('name', 'Unknown')
                description = properties.get('description', 'No description')
                output += f"- [{entity_type}] {name}\n"
                output += f"  URN: {urn}\n"
                output += f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}\n\n"
        else:
            output += "No entities found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_search_entities_tool: {e}")
        return f"Error: {str(e)}"


async def datahub_get_entity_tool(project_id: str, urn: str) -> str:
    """
    Get details of a specific DataHub entity by URN.

    Args:
        project_id: Project ID for credential lookup
        urn: Entity URN to retrieve

    Returns:
        Entity details formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.get_entity(urn)

        if "error" in result:
            return f"Error getting entity: {result['error']}"

        entity = result.get('entity', {})

        output = f"DataHub Entity Details\n"
        output += f"URN: {entity.get('urn', 'Unknown')}\n"
        output += f"Type: {entity.get('type', 'Unknown')}\n"

        properties = entity.get('properties', {})
        if properties:
            output += f"Name: {properties.get('name', 'Unknown')}\n"
            output += f"Description: {properties.get('description', 'No description')}\n"

        platform = entity.get('platform', {})
        if platform:
            output += f"Platform: {platform.get('name', 'Unknown')}\n"

        # Schema information for datasets
        schema_metadata = entity.get('schemaMetadata', {})
        if schema_metadata:
            fields = schema_metadata.get('fields', [])
            if fields:
                output += f"\nSchema Fields ({len(fields)}):\n"
                for field in fields[:10]:  # Show first 10 fields
                    field_path = field.get('fieldPath', 'Unknown')
                    data_type = field.get('nativeDataType', 'Unknown')
                    description = field.get('description', 'No description')
                    output += f"- {field_path} ({data_type}): {description}\n"
                
                if len(fields) > 10:
                    output += f"... and {len(fields) - 10} more fields\n"

        # Charts for dashboards
        charts = entity.get('charts', [])
        if charts:
            output += f"\nCharts ({len(charts)}):\n"
            for chart in charts[:5]:  # Show first 5 charts
                chart_urn = chart.get('urn', 'Unknown')
                output += f"- {chart_urn}\n"

            if len(charts) > 5:
                output += f"... and {len(charts) - 5} more charts\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_get_entity_tool: {e}")
        return f"Error: {str(e)}"


async def datahub_list_datasets_tool(project_id: str, platform: Optional[str] = None, 
                                     start: int = 0, count: int = 20) -> str:
    """
    List datasets in DataHub.

    Args:
        project_id: Project ID for credential lookup
        platform: Optional platform name to filter by
        start: Start index for pagination
        count: Number of results per page

    Returns:
        List of datasets formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.list_datasets(platform, start, count)

        if "error" in result:
            return f"Error listing datasets: {result['error']}"

        datasets = result.get('datasets', [])
        total_count = result.get('total', len(datasets))

        output = f"DataHub Datasets (Page {start//count + 1}): {len(datasets)} of {total_count} total\n"
        if platform:
            output += f"Platform: {platform}\n"
        output += "\n"

        if datasets:
            for item in datasets:
                entity = item.get('entity', {})
                urn = entity.get('urn', 'Unknown')
                properties = entity.get('properties', {})
                name = properties.get('name', 'Unknown')
                description = properties.get('description', 'No description')
                output += f"- {name}\n"
                output += f"  URN: {urn}\n"
                output += f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}\n\n"
        else:
            output += "No datasets found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_list_datasets_tool: {e}")
        return f"Error: {str(e)}"


async def datahub_list_dashboards_tool(project_id: str, start: int = 0, count: int = 20) -> str:
    """
    List dashboards in DataHub.

    Args:
        project_id: Project ID for credential lookup
        start: Start index for pagination
        count: Number of results per page

    Returns:
        List of dashboards formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.list_dashboards(start, count)

        if "error" in result:
            return f"Error listing dashboards: {result['error']}"

        dashboards = result.get('dashboards', [])
        total_count = result.get('total', len(dashboards))

        output = f"DataHub Dashboards (Page {start//count + 1}): {len(dashboards)} of {total_count} total\n\n"

        if dashboards:
            for item in dashboards:
                entity = item.get('entity', {})
                urn = entity.get('urn', 'Unknown')
                properties = entity.get('properties', {})
                name = properties.get('name', 'Unknown')
                description = properties.get('description', 'No description')
                output += f"- {name}\n"
                output += f"  URN: {urn}\n"
                output += f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}\n\n"
        else:
            output += "No dashboards found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_list_dashboards_tool: {e}")
        return f"Error: {str(e)}"


async def datahub_list_charts_tool(project_id: str, start: int = 0, count: int = 20) -> str:
    """
    List charts in DataHub.

    Args:
        project_id: Project ID for credential lookup
        start: Start index for pagination
        count: Number of results per page

    Returns:
        List of charts formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.list_charts(start, count)

        if "error" in result:
            return f"Error listing charts: {result['error']}"

        charts = result.get('charts', [])
        total_count = result.get('total', len(charts))

        output = f"DataHub Charts (Page {start//count + 1}): {len(charts)} of {total_count} total\n\n"

        if charts:
            for item in charts:
                entity = item.get('entity', {})
                urn = entity.get('urn', 'Unknown')
                properties = entity.get('properties', {})
                name = properties.get('name', 'Unknown')
                description = properties.get('description', 'No description')
                output += f"- {name}\n"
                output += f"  URN: {urn}\n"
                output += f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}\n\n"
        else:
            output += "No charts found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_list_charts_tool: {e}")
        return f"Error: {str(e)}"


async def datahub_get_lineage_tool(project_id: str, urn: str, direction: str = "DOWNSTREAM", 
                                   start: int = 0, count: int = 100) -> str:
    """
    Get lineage information for a DataHub entity.

    Args:
        project_id: Project ID for credential lookup
        urn: Entity URN to get lineage for
        direction: Lineage direction (UPSTREAM or DOWNSTREAM)
        start: Start index for pagination
        count: Number of results per page

    Returns:
        Lineage information formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.get_lineage(urn, direction, start, count)

        if "error" in result:
            return f"Error getting lineage: {result['error']}"

        lineage = result.get('lineage', [])
        total_count = result.get('total', len(lineage))
        lineage_direction = result.get('direction', direction)

        output = f"DataHub Lineage ({lineage_direction})\n"
        output += f"Entity URN: {urn}\n"
        output += f"Related entities: {len(lineage)} of {total_count} total\n\n"

        if lineage:
            for relationship in lineage:
                entity = relationship.get('entity', {})
                related_urn = entity.get('urn', 'Unknown')
                entity_type = entity.get('type', 'Unknown')
                properties = entity.get('properties', {})
                name = properties.get('name', 'Unknown')
                output += f"- [{entity_type}] {name}\n"
                output += f"  URN: {related_urn}\n\n"
        else:
            output += f"No {lineage_direction.lower()} lineage found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_get_lineage_tool: {e}")
        return f"Error: {str(e)}"


async def datahub_list_platforms_tool(project_id: str) -> str:
    """
    List all platforms in DataHub.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        List of platforms formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.get_platform_instances()

        if "error" in result:
            return f"Error listing platforms: {result['error']}"

        platforms = result.get('platforms', [])
        total_count = result.get('total', len(platforms))

        output = f"DataHub Platforms: {len(platforms)} of {total_count} total\n\n"

        if platforms:
            for platform in platforms:
                urn = platform.get('urn', 'Unknown')
                name = platform.get('name', 'Unknown')
                platform_type = platform.get('type', 'Unknown')
                properties = platform.get('properties', {})
                display_name = properties.get('displayName', name)
                output += f"- {display_name} ({name})\n"
                output += f"  Type: {platform_type}\n"
                output += f"  URN: {urn}\n\n"
        else:
            output += "No platforms found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_list_platforms_tool: {e}")
        return f"Error: {str(e)}"


async def datahub_list_tags_tool(project_id: str, start: int = 0, count: int = 20) -> str:
    """
    List all tags in DataHub.

    Args:
        project_id: Project ID for credential lookup
        start: Start index for pagination
        count: Number of results per page

    Returns:
        List of tags formatted as a string
    """
    try:
        provider = await get_provider(project_id, "datahub")
        if not provider:
            return "Error: Could not get DataHub provider for project"

        result = await provider.get_tags(start, count)

        if "error" in result:
            return f"Error listing tags: {result['error']}"

        tags = result.get('tags', [])
        total_count = result.get('total', len(tags))

        output = f"DataHub Tags (Page {start//count + 1}): {len(tags)} of {total_count} total\n\n"

        if tags:
            for tag in tags:
                urn = tag.get('urn', 'Unknown')
                name = tag.get('name', 'Unknown')
                description = tag.get('description', 'No description')
                output += f"- {name}\n"
                output += f"  URN: {urn}\n"
                output += f"  Description: {description}\n\n"
        else:
            output += "No tags found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in datahub_list_tags_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# ATLAN TOOLS
# =============================================================================

async def atlan_search_assets_tool(project_id: str, query: str = "*",
                                   asset_types: Optional[List[str]] = None,
                                   from_: int = 0, size: int = 25) -> str:
    """Search for assets in Atlan data catalog."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.search_assets(query, asset_types, from_, size)

        if "error" in result:
            return f"Error searching assets: {result['error']}"

        entities = result.get('entities', [])
        total = result.get('approximateCount', len(entities))

        output = f"Atlan Search Results (Page {from_//size + 1}): {len(entities)} of {total} total\n"
        output += f"Query: {query}\n"
        if asset_types:
            output += f"Asset Types: {', '.join(asset_types)}\n"
        output += "\n"

        for entity in entities:
            attrs = entity.get('attributes', {})
            output += f"- [{entity.get('typeName', 'Unknown')}] {attrs.get('name', 'Unknown')}\n"
            output += f"  GUID: {entity.get('guid', 'Unknown')}\n"
            if attrs.get('description'):
                desc = attrs['description'][:100]
                output += f"  Description: {desc}{'...' if len(attrs['description']) > 100 else ''}\n"
            output += "\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_search_assets_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_search_by_type_tool(project_id: str, type_name: str,
                                    from_: int = 0, size: int = 25) -> str:
    """Search for all assets of a specific type."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.search_by_type(type_name, from_, size)

        if "error" in result:
            return f"Error searching by type: {result['error']}"

        entities = result.get('entities', [])
        total = result.get('approximateCount', len(entities))

        output = f"Atlan {type_name} Assets: {len(entities)} of {total} total\n\n"

        for entity in entities:
            attrs = entity.get('attributes', {})
            output += f"- {attrs.get('name', 'Unknown')}\n"
            output += f"  GUID: {entity.get('guid')}\n"
            output += f"  Qualified Name: {attrs.get('qualifiedName', 'N/A')}\n\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_search_by_type_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_get_asset_tool(project_id: str, guid: str) -> str:
    """Get detailed information about a specific asset by GUID."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.get_asset(guid)

        if "error" in result:
            return f"Error getting asset: {result['error']}"

        entity = result.get('entity', {})
        attrs = entity.get('attributes', {})

        output = f"Atlan Asset Details\n{'='*50}\n"
        output += f"Type: {entity.get('typeName', 'Unknown')}\n"
        output += f"GUID: {entity.get('guid', 'Unknown')}\n"
        output += f"Name: {attrs.get('name', 'Unknown')}\n"
        output += f"Qualified Name: {attrs.get('qualifiedName', 'N/A')}\n"
        output += f"Description: {attrs.get('description', 'No description')}\n"
        output += f"Owner: {attrs.get('ownerUsers', [])}\n"
        output += f"Certificate: {attrs.get('certificateStatus', 'N/A')}\n"

        classifications = entity.get('classifications', [])
        if classifications:
            output += f"\nClassifications: {', '.join([c.get('typeName', '') for c in classifications])}\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_get_asset_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_get_asset_by_qualified_name_tool(project_id: str, type_name: str,
                                                  qualified_name: str) -> str:
    """Get asset by type and qualified name."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.get_asset_by_qualified_name(type_name, qualified_name)

        if "error" in result:
            return f"Error getting asset: {result['error']}"

        entity = result.get('entity', result)
        attrs = entity.get('attributes', {})

        output = f"Asset: {attrs.get('name', 'Unknown')}\n"
        output += f"GUID: {entity.get('guid', 'Unknown')}\n"
        output += f"Type: {entity.get('typeName', type_name)}\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_get_asset_by_qualified_name_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_create_asset_tool(project_id: str, type_name: str, name: str,
                                  qualified_name: str, description: Optional[str] = None) -> str:
    """Create a new asset in Atlan."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        entity = {
            "typeName": type_name,
            "attributes": {
                "name": name,
                "qualifiedName": qualified_name
            }
        }
        if description:
            entity["attributes"]["description"] = description

        result = await provider.create_asset(entity)

        if "error" in result:
            return f"Error creating asset: {result['error']}"

        created = result.get('guidAssignments', {})
        return f"Successfully created {type_name}: {name}\nGUID: {list(created.values())[0] if created else 'Unknown'}"
    except Exception as e:
        logger.error(f"Error in atlan_create_asset_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_update_asset_tool(project_id: str, guid: str, attributes: Dict[str, Any]) -> str:
    """Update an existing asset in Atlan."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        entity = {"guid": guid, "attributes": attributes}
        result = await provider.update_asset(entity)

        if "error" in result:
            return f"Error updating asset: {result['error']}"

        return f"Successfully updated asset {guid}"
    except Exception as e:
        logger.error(f"Error in atlan_update_asset_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_delete_asset_tool(project_id: str, guid: str, hard_delete: bool = False) -> str:
    """Delete an asset from Atlan."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.delete_asset(guid, hard_delete)

        if "error" in result:
            return f"Error deleting asset: {result['error']}"

        delete_type = "permanently deleted" if hard_delete else "soft deleted"
        return f"Successfully {delete_type} asset {guid}"
    except Exception as e:
        logger.error(f"Error in atlan_delete_asset_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_update_asset_description_tool(project_id: str, guid: str, description: str) -> str:
    """Update the description of an asset."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.update_asset_description(guid, description)

        if "error" in result:
            return f"Error updating description: {result['error']}"

        return f"Successfully updated description for asset {guid}"
    except Exception as e:
        logger.error(f"Error in atlan_update_asset_description_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_update_asset_owners_tool(project_id: str, guid: str,
                                         owner_users: Optional[List[str]] = None,
                                         owner_groups: Optional[List[str]] = None) -> str:
    """Update the owners of an asset."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.update_asset_owners(guid, owner_users, owner_groups)

        if "error" in result:
            return f"Error updating owners: {result['error']}"

        return f"Successfully updated owners for asset {guid}"
    except Exception as e:
        logger.error(f"Error in atlan_update_asset_owners_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_get_lineage_tool(project_id: str, guid: str,
                                  direction: str = "BOTH", depth: int = 3) -> str:
    """Get lineage information for an asset."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.get_lineage(guid, direction, min(depth, 10))

        if "error" in result:
            return f"Error getting lineage: {result['error']}"

        relations = result.get('relations', [])
        entities = result.get('guidEntityMap', {})

        output = f"Atlan Lineage for {guid}\n"
        output += f"Direction: {direction}, Depth: {depth}\n{'='*50}\n"
        output += f"Related Assets: {len(entities)}\n"
        output += f"Relations: {len(relations)}\n\n"

        upstream = [r for r in relations if r.get('toEntityId') == guid]
        downstream = [r for r in relations if r.get('fromEntityId') == guid]

        if upstream:
            output += f"Upstream ({len(upstream)}):\n"
            for r in upstream[:10]:
                from_id = r.get('fromEntityId')
                entity = entities.get(from_id, {})
                attrs = entity.get('attributes', {})
                output += f"  <- [{entity.get('typeName', '?')}] {attrs.get('name', from_id)}\n"

        if downstream:
            output += f"\nDownstream ({len(downstream)}):\n"
            for r in downstream[:10]:
                to_id = r.get('toEntityId')
                entity = entities.get(to_id, {})
                attrs = entity.get('attributes', {})
                output += f"  -> [{entity.get('typeName', '?')}] {attrs.get('name', to_id)}\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_get_lineage_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_glossaries_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List all glossaries in Atlan."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_glossaries(from_, size)

        if "error" in result:
            return f"Error listing glossaries: {result['error']}"

        entities = result.get('entities', [])
        output = f"Atlan Glossaries: {len(entities)}\n\n"

        for entity in entities:
            attrs = entity.get('attributes', {})
            output += f"- {attrs.get('name', 'Unknown')}\n"
            output += f"  GUID: {entity.get('guid')}\n\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_list_glossaries_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_get_glossary_tool(project_id: str, guid: str) -> str:
    """Get a specific glossary by GUID."""
    return await atlan_get_asset_tool(project_id, guid)


async def atlan_list_glossary_terms_tool(project_id: str, glossary_guid: Optional[str] = None,
                                          from_: int = 0, size: int = 25) -> str:
    """List glossary terms."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_glossary_terms(glossary_guid, from_, size)

        if "error" in result:
            return f"Error listing glossary terms: {result['error']}"

        entities = result.get('entities', [])
        output = f"Atlan Glossary Terms: {len(entities)}\n\n"

        for entity in entities:
            attrs = entity.get('attributes', {})
            output += f"- {attrs.get('name', 'Unknown')}\n"
            output += f"  GUID: {entity.get('guid')}\n"
            if attrs.get('description'):
                output += f"  Description: {attrs['description'][:100]}\n"
            output += "\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_list_glossary_terms_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_get_glossary_term_tool(project_id: str, guid: str) -> str:
    """Get a specific glossary term by GUID."""
    return await atlan_get_asset_tool(project_id, guid)


async def atlan_create_glossary_term_tool(project_id: str, name: str, glossary_guid: str,
                                          description: Optional[str] = None,
                                          short_description: Optional[str] = None) -> str:
    """Create a new glossary term."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.create_glossary_term(name, glossary_guid, description, short_description)

        if "error" in result:
            return f"Error creating glossary term: {result['error']}"

        return f"Successfully created glossary term: {name}"
    except Exception as e:
        logger.error(f"Error in atlan_create_glossary_term_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_glossary_categories_tool(project_id: str, glossary_guid: Optional[str] = None,
                                               from_: int = 0, size: int = 25) -> str:
    """List glossary categories."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_glossary_categories(glossary_guid, from_, size)

        if "error" in result:
            return f"Error listing categories: {result['error']}"

        entities = result.get('entities', [])
        output = f"Atlan Glossary Categories: {len(entities)}\n\n"

        for entity in entities:
            attrs = entity.get('attributes', {})
            output += f"- {attrs.get('name', 'Unknown')}\n"
            output += f"  GUID: {entity.get('guid')}\n\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_list_glossary_categories_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_link_term_to_asset_tool(project_id: str, term_guid: str, asset_guid: str) -> str:
    """Link a glossary term to an asset."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.link_term_to_asset(term_guid, asset_guid)

        if "error" in result:
            return f"Error linking term: {result['error']}"

        return f"Successfully linked term {term_guid} to asset {asset_guid}"
    except Exception as e:
        logger.error(f"Error in atlan_link_term_to_asset_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_classifications_tool(project_id: str) -> str:
    """List all classification types (tags) in Atlan."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_classifications()

        if "error" in result:
            return f"Error listing classifications: {result['error']}"

        classifications = result.get('classifications', [])
        output = f"Atlan Classifications: {len(classifications)}\n\n"

        for c in classifications:
            output += f"- {c.get('name', 'Unknown')}\n"
            if c.get('description'):
                output += f"  Description: {c['description']}\n"
            output += "\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_list_classifications_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_add_classification_tool(project_id: str, guid: str, classification_name: str) -> str:
    """Add a classification (tag) to an asset."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.add_classification_to_asset(guid, classification_name)

        if "error" in result:
            return f"Error adding classification: {result['error']}"

        return f"Successfully added classification '{classification_name}' to asset {guid}"
    except Exception as e:
        logger.error(f"Error in atlan_add_classification_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_remove_classification_tool(project_id: str, guid: str, classification_name: str) -> str:
    """Remove a classification from an asset."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.remove_classification_from_asset(guid, classification_name)

        if "error" in result:
            return f"Error removing classification: {result['error']}"

        return f"Successfully removed classification '{classification_name}' from asset {guid}"
    except Exception as e:
        logger.error(f"Error in atlan_remove_classification_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_tables_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List all table assets in Atlan."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_tables(from_, size)
        return _format_atlan_asset_list(result, "Tables")
    except Exception as e:
        logger.error(f"Error in atlan_list_tables_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_columns_tool(project_id: str, table_guid: Optional[str] = None,
                                   from_: int = 0, size: int = 25) -> str:
    """List columns, optionally filtered by parent table."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_columns(table_guid, from_, size)
        return _format_atlan_asset_list(result, "Columns")
    except Exception as e:
        logger.error(f"Error in atlan_list_columns_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_databases_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List all database assets."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_databases(from_, size)
        return _format_atlan_asset_list(result, "Databases")
    except Exception as e:
        logger.error(f"Error in atlan_list_databases_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_schemas_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List all schema assets."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_schemas(from_, size)
        return _format_atlan_asset_list(result, "Schemas")
    except Exception as e:
        logger.error(f"Error in atlan_list_schemas_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_dashboards_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List all BI dashboard assets."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_dashboards(from_, size)
        return _format_atlan_asset_list(result, "Dashboards")
    except Exception as e:
        logger.error(f"Error in atlan_list_dashboards_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_dbt_models_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List dbt model assets."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_dbt_models(from_, size)
        return _format_atlan_asset_list(result, "dbt Models")
    except Exception as e:
        logger.error(f"Error in atlan_list_dbt_models_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_airflow_dags_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List Airflow DAG assets."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_airflow_dags(from_, size)
        return _format_atlan_asset_list(result, "Airflow DAGs")
    except Exception as e:
        logger.error(f"Error in atlan_list_airflow_dags_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_kafka_topics_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List Kafka topic assets."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_kafka_topics(from_, size)
        return _format_atlan_asset_list(result, "Kafka Topics")
    except Exception as e:
        logger.error(f"Error in atlan_list_kafka_topics_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_list_s3_objects_tool(project_id: str, from_: int = 0, size: int = 25) -> str:
    """List S3 and cloud storage assets."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.list_s3_objects(from_, size)
        return _format_atlan_asset_list(result, "Cloud Storage Objects")
    except Exception as e:
        logger.error(f"Error in atlan_list_s3_objects_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_update_custom_metadata_tool(project_id: str, guid: str,
                                             custom_metadata_name: str,
                                             attributes: Dict[str, Any]) -> str:
    """Update custom metadata on an asset."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.update_custom_metadata(guid, custom_metadata_name, attributes)

        if "error" in result:
            return f"Error updating custom metadata: {result['error']}"

        return f"Successfully updated custom metadata '{custom_metadata_name}' on asset {guid}"
    except Exception as e:
        logger.error(f"Error in atlan_update_custom_metadata_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_get_custom_metadata_types_tool(project_id: str) -> str:
    """Get all custom metadata type definitions."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.get_custom_metadata_types()

        if "error" in result:
            return f"Error getting custom metadata types: {result['error']}"

        types = result.get('customMetadataTypes', [])
        output = f"Atlan Custom Metadata Types: {len(types)}\n\n"

        for t in types:
            output += f"- {t.get('name', 'Unknown')}\n"
            if t.get('description'):
                output += f"  Description: {t['description']}\n"
            output += "\n"

        return output
    except Exception as e:
        logger.error(f"Error in atlan_get_custom_metadata_types_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_certify_asset_tool(project_id: str, guid: str,
                                    status: str = "VERIFIED",
                                    message: Optional[str] = None) -> str:
    """Certify an asset with a status."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.certify_asset(guid, status, message)

        if "error" in result:
            return f"Error certifying asset: {result['error']}"

        return f"Successfully certified asset {guid} with status: {status}"
    except Exception as e:
        logger.error(f"Error in atlan_certify_asset_tool: {e}")
        return f"Error: {str(e)}"


async def atlan_bulk_update_assets_tool(project_id: str, entities: List[Dict[str, Any]]) -> str:
    """Update multiple assets in a single request."""
    try:
        provider = await get_provider(project_id, "atlan")
        if not provider:
            return "Error: Could not get Atlan provider for project"

        result = await provider.bulk_update_assets(entities)

        if "error" in result:
            return f"Error in bulk update: {result['error']}"

        return f"Successfully updated {len(entities)} assets"
    except Exception as e:
        logger.error(f"Error in atlan_bulk_update_assets_tool: {e}")
        return f"Error: {str(e)}"


def _format_atlan_asset_list(result: Dict[str, Any], asset_type: str) -> str:
    """Helper to format asset list results."""
    if "error" in result:
        return f"Error listing {asset_type.lower()}: {result['error']}"

    entities = result.get('entities', [])
    total = result.get('approximateCount', len(entities))
    output = f"Atlan {asset_type}: {len(entities)} of {total} total\n\n"

    for entity in entities:
        attrs = entity.get('attributes', {})
        output += f"- [{entity.get('typeName', '?')}] {attrs.get('name', 'Unknown')}\n"
        output += f"  GUID: {entity.get('guid')}\n"
        output += f"  Qualified Name: {attrs.get('qualifiedName', 'N/A')}\n\n"

    return output


# =============================================================================
# OPENAPI TOOLS
# =============================================================================

async def openapi_get_spec_tool(project_id: str) -> str:
    """
    Get the OpenAPI specification for the configured API.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        OpenAPI specification summary formatted as a string
    """
    try:
        provider = await get_provider(project_id, "openapi")
        if not provider:
            return "Error: Could not get OpenAPI provider for project"

        result = await provider.get_spec()

        if "error" in result:
            return f"Error getting OpenAPI spec: {result['error']}"

        spec = result.get('spec', {})
        info = spec.get('info', {})
        paths = spec.get('paths', {})

        output = f"OpenAPI Specification\n"
        output += f"Title: {info.get('title', 'Unknown')}\n"
        output += f"Version: {info.get('version', 'Unknown')}\n"
        output += f"Description: {info.get('description', 'No description')}\n"
        output += f"Base URL: {result.get('base_url', 'Unknown')}\n"
        output += f"Endpoints: {len(paths)}\n\n"

        if paths:
            output += "Available Endpoints:\n"
            for path, methods in paths.items():
                method_list = list(methods.keys())
                output += f"- {path} ({', '.join(method_list)})\n"

        return output

    except Exception as e:
        logger.error(f"Error in openapi_get_spec_tool: {e}")
        return f"Error: {str(e)}"


async def openapi_list_endpoints_tool(project_id: str, tag: Optional[str] = None) -> str:
    """
    List all available endpoints in the OpenAPI specification.

    Args:
        project_id: Project ID for credential lookup
        tag: Optional tag to filter endpoints

    Returns:
        List of endpoints formatted as a string
    """
    try:
        provider = await get_provider(project_id, "openapi")
        if not provider:
            return "Error: Could not get OpenAPI provider for project"

        result = await provider.list_endpoints(tag)

        if "error" in result:
            return f"Error listing endpoints: {result['error']}"

        endpoints = result.get('endpoints', [])

        output = f"OpenAPI Endpoints: {len(endpoints)} found\n"
        if tag:
            output += f"Filtered by tag: {tag}\n"
        output += "\n"

        if endpoints:
            for endpoint in endpoints:
                method = endpoint.get('method', 'Unknown').upper()
                path = endpoint.get('path', 'Unknown')
                summary = endpoint.get('summary', 'No summary')
                tags = endpoint.get('tags', [])
                output += f"- {method} {path}\n"
                output += f"  Summary: {summary}\n"
                if tags:
                    output += f"  Tags: {', '.join(tags)}\n"
                output += "\n"
        else:
            output += "No endpoints found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in openapi_list_endpoints_tool: {e}")
        return f"Error: {str(e)}"


async def openapi_call_endpoint_tool(project_id: str, method: str, path: str,
                                     parameters: Optional[Dict[str, Any]] = None,
                                     data: Optional[Dict[str, Any]] = None,
                                     headers: Optional[Dict[str, str]] = None) -> str:
    """
    Call a specific endpoint in the OpenAPI specification.

    Args:
        project_id: Project ID for credential lookup
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API endpoint path
        parameters: Query parameters
        data: Request body data
        headers: Additional headers

    Returns:
        API response formatted as a string
    """
    try:
        provider = await get_provider(project_id, "openapi")
        if not provider:
            return "Error: Could not get OpenAPI provider for project"

        result = await provider.call_endpoint(method, path, parameters, data, headers)

        if "error" in result:
            return f"Error calling endpoint: {result['error']}"

        response = result.get('response', {})
        status_code = response.get('status_code', 'Unknown')
        response_data = response.get('data', {})
        response_headers = response.get('headers', {})

        output = f"OpenAPI Endpoint Call\n"
        output += f"Method: {method.upper()}\n"
        output += f"Path: {path}\n"
        output += f"Status Code: {status_code}\n"

        if parameters:
            output += f"Parameters: {parameters}\n"

        if data:
            output += f"Request Data: {data}\n"

        if response_headers:
            output += f"Response Headers: {dict(response_headers)}\n"

        output += f"\nResponse Data:\n"

        # Format response data nicely
        if isinstance(response_data, dict):
            if len(str(response_data)) > 1000:
                # Truncate long responses
                output += f"{str(response_data)[:1000]}...\n[Response truncated]\n"
            else:
                output += f"{response_data}\n"
        elif isinstance(response_data, list):
            output += f"Array with {len(response_data)} items\n"
            if response_data and len(response_data) <= 5:
                for i, item in enumerate(response_data):
                    output += f"Item {i + 1}: {item}\n"
            elif response_data:
                output += f"First item: {response_data[0]}\n"
                output += f"... and {len(response_data) - 1} more items\n"
        else:
            output += f"{response_data}\n"

        return output

    except Exception as e:
        logger.error(f"Error in openapi_call_endpoint_tool: {e}")
        return f"Error: {str(e)}"


async def openapi_get_endpoint_schema_tool(project_id: str, method: str, path: str) -> str:
    """
    Get the schema definition for a specific endpoint.

    Args:
        project_id: Project ID for credential lookup
        method: HTTP method
        path: API endpoint path

    Returns:
        Endpoint schema formatted as a string
    """
    try:
        provider = await get_provider(project_id, "openapi")
        if not provider:
            return "Error: Could not get OpenAPI provider for project"

        result = await provider.get_endpoint_schema(method, path)

        if "error" in result:
            return f"Error getting endpoint schema: {result['error']}"

        schema = result.get('schema', {})

        output = f"OpenAPI Endpoint Schema\n"
        output += f"Method: {method.upper()}\n"
        output += f"Path: {path}\n"
        output += f"Summary: {schema.get('summary', 'No summary')}\n"
        output += f"Description: {schema.get('description', 'No description')}\n\n"

        # Parameters
        parameters = schema.get('parameters', [])
        if parameters:
            output += "Parameters:\n"
            for param in parameters:
                param_name = param.get('name', 'Unknown')
                param_in = param.get('in', 'Unknown')
                param_type = param.get('schema', {}).get('type', 'Unknown')
                required = param.get('required', False)
                description = param.get('description', 'No description')
                output += f"- {param_name} ({param_in}) - {param_type} {'[Required]' if required else '[Optional]'}\n"
                output += f"  {description}\n"
            output += "\n"

        # Request body
        request_body = schema.get('requestBody', {})
        if request_body:
            output += "Request Body:\n"
            content = request_body.get('content', {})
            for content_type, content_schema in content.items():
                output += f"- Content-Type: {content_type}\n"
                schema_info = content_schema.get('schema', {})
                output += f"  Type: {schema_info.get('type', 'Unknown')}\n"
            output += "\n"

        # Responses
        responses = schema.get('responses', {})
        if responses:
            output += "Responses:\n"
            for status_code, response_info in responses.items():
                description = response_info.get('description', 'No description')
                output += f"- {status_code}: {description}\n"

        return output

    except Exception as e:
        logger.error(f"Error in openapi_get_endpoint_schema_tool: {e}")
        return f"Error: {str(e)}"


# =============================================================================
# AIRFLOW TOOLS
# =============================================================================

async def airflow_list_dags_tool(project_id: str, limit: int = 100, offset: int = 0, only_active: bool = True) -> str:
    """
    List all DAGs in Airflow.
    
    Args:
        project_id: Project identifier for credential lookup
        limit: Maximum number of DAGs to return (default: 100)
        offset: Number of DAGs to skip (default: 0)
        only_active: Only return active DAGs (default: True)
    
    Returns:
        JSON string with list of DAGs
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.list_dags(
            limit=limit,
            offset=offset,
            only_active=only_active
        )
        
        if "error" in result:
            return f"Error listing DAGs: {result['error']}"
        
        dags = result.get("dags", [])
        total = result.get("total_entries", 0)
        
        response = f"Found {len(dags)} DAGs (total: {total}):\n\n"
        for dag in dags[:10]:  # Show first 10
            dag_id = dag.get("dag_id", "N/A")
            is_active = dag.get("is_active", False)
            is_paused = dag.get("is_paused", True)
            description = dag.get("description", "No description")
            
            status = "active" if is_active and not is_paused else "inactive"
            response += f"• {dag_id} ({status})\n"
            response += f"  Description: {description}\n\n"
        
        if len(dags) > 10:
            response += f"... and {len(dags) - 10} more DAGs\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_list_dags_tool: {e}")
        return f"Failed to list DAGs: {str(e)}"


async def airflow_get_dag_tool(project_id: str, dag_id: str) -> str:
    """
    Get details of a specific DAG.
    
    Args:
        project_id: Project identifier for credential lookup
        dag_id: DAG identifier
    
    Returns:
        JSON string with DAG details
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.get_dag(dag_id)
        
        if "error" in result:
            return f"Error getting DAG: {result['error']}"
        
        dag = result.get("dag", {})
        
        response = f"DAG Details: {dag_id}\n\n"
        response += f"• Active: {dag.get('is_active', False)}\n"
        response += f"• Paused: {dag.get('is_paused', True)}\n"
        response += f"• Schedule: {dag.get('schedule_interval', 'None')}\n"
        response += f"• Description: {dag.get('description', 'No description')}\n"
        tags = dag.get('tags', [])
        tag_names = [tag['name'] for tag in tags] if tags else []
        response += f"• Tags: {', '.join(tag_names)}\n"
        response += f"• File Location: {dag.get('fileloc', 'N/A')}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_get_dag_tool: {e}", exc_info=True)
        return f"Failed to get DAG details: {str(e)}"


async def airflow_trigger_dag_tool(project_id: str, dag_id: str, conf: Optional[Dict[str, Any]] = None) -> str:
    """
    Trigger a DAG run.
    
    Args:
        project_id: Project identifier for credential lookup
        dag_id: DAG identifier
        conf: Configuration dictionary for the DAG run (optional)
    
    Returns:
        JSON string with DAG run details
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.trigger_dag(dag_id, conf)
        
        if "error" in result:
            return f"Error triggering DAG: {result['error']}"
        
        dag_run = result.get("dag_run", {})
        
        response = f"DAG Run Triggered: {dag_id}\n\n"
        response += f"• Run ID: {dag_run.get('dag_run_id', 'N/A')}\n"
        response += f"• State: {dag_run.get('state', 'N/A')}\n"
        response += f"• Start Date: {dag_run.get('start_date', 'N/A')}\n"
        response += f"• Execution Date: {dag_run.get('execution_date', 'N/A')}\n"
        
        if conf:
            response += f"• Configuration: {conf}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_trigger_dag_tool: {e}")
        return f"Failed to trigger DAG: {str(e)}"


async def airflow_get_dag_runs_tool(project_id: str, dag_id: str, limit: int = 25, offset: int = 0) -> str:
    """
    Get DAG runs for a specific DAG.
    
    Args:
        project_id: Project identifier for credential lookup
        dag_id: DAG identifier
        limit: Maximum number of runs to return (default: 25)
        offset: Number of runs to skip (default: 0)
    
    Returns:
        JSON string with DAG runs
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.get_dag_runs(dag_id, limit, offset)
        
        if "error" in result:
            return f"Error getting DAG runs: {result['error']}"
        
        dag_runs = result.get("dag_runs", [])
        total = result.get("total_entries", 0)
        
        response = f"DAG Runs for {dag_id} (showing {len(dag_runs)} of {total}):\n\n"
        
        for run in dag_runs[:10]:  # Show first 10
            run_id = run.get('dag_run_id', 'N/A')
            state = run.get('state', 'N/A')
            start_date = run.get('start_date', 'N/A')
            end_date = run.get('end_date', 'N/A')
            
            response += f"• {run_id} - {state}\n"
            response += f"  Start: {start_date}\n"
            if end_date:
                response += f"  End: {end_date}\n"
            response += "\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_get_dag_runs_tool: {e}")
        return f"Failed to get DAG runs: {str(e)}"


async def airflow_get_task_instances_tool(project_id: str, dag_id: str, dag_run_id: str) -> str:
    """
    Get task instances for a DAG run.
    
    Args:
        project_id: Project identifier for credential lookup
        dag_id: DAG identifier
        dag_run_id: DAG run identifier
    
    Returns:
        JSON string with task instances
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.get_task_instances(dag_id, dag_run_id)
        
        if "error" in result:
            return f"Error getting task instances: {result['error']}"
        
        task_instances = result.get("task_instances", [])
        
        response = f"Task Instances for {dag_id} / {dag_run_id}:\n\n"
        
        for task in task_instances:
            task_id = task.get('task_id', 'N/A')
            state = task.get('state', 'N/A')
            start_date = task.get('start_date', 'N/A')
            end_date = task.get('end_date', 'N/A')
            
            response += f"• {task_id} - {state}\n"
            response += f"  Start: {start_date}\n"
            if end_date:
                response += f"  End: {end_date}\n"
            response += "\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_get_task_instances_tool: {e}")
        return f"Failed to get task instances: {str(e)}"


async def airflow_get_task_logs_tool(project_id: str, dag_id: str, dag_run_id: str, task_id: str, task_try_number: int = 1) -> str:
    """
    Get logs for a task instance.
    
    Args:
        project_id: Project identifier for credential lookup
        dag_id: DAG identifier
        dag_run_id: DAG run identifier
        task_id: Task identifier
        task_try_number: Task try number (default: 1)
    
    Returns:
        JSON string with task logs
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.get_task_logs(dag_id, dag_run_id, task_id, task_try_number)
        
        if "error" in result:
            return f"Error getting task logs: {result['error']}"
        
        logs = result.get("logs", "")
        
        response = f"Logs for {dag_id} / {dag_run_id} / {task_id} (try {task_try_number}):\n\n"
        response += logs
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_get_task_logs_tool: {e}")
        return f"Failed to get task logs: {str(e)}"


async def airflow_pause_dag_tool(project_id: str, dag_id: str) -> str:
    """
    Pause a DAG.
    
    Args:
        project_id: Project identifier for credential lookup
        dag_id: DAG identifier
    
    Returns:
        JSON string with operation result
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.pause_dag(dag_id)
        
        if "error" in result:
            return f"Error pausing DAG: {result['error']}"
        
        response = f"DAG {dag_id} has been paused successfully."
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_pause_dag_tool: {e}")
        return f"Failed to pause DAG: {str(e)}"


async def airflow_unpause_dag_tool(project_id: str, dag_id: str) -> str:
    """
    Unpause a DAG.
    
    Args:
        project_id: Project identifier for credential lookup
        dag_id: DAG identifier
    
    Returns:
        JSON string with operation result
    """
    try:
        provider = await get_provider(project_id, "airflow")
        
        result = await provider.unpause_dag(dag_id)
        
        if "error" in result:
            return f"Error unpausing DAG: {result['error']}"
        
        response = f"DAG {dag_id} has been unpaused successfully."
        
        return response
        
    except Exception as e:
        logger.error(f"Error in airflow_unpause_dag_tool: {e}")
        return f"Failed to unpause DAG: {str(e)}"


# =============================================================================
# PROJECT-SPECIFIC MCP ENDPOINT
# =============================================================================

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
        
        # Get supported providers and available tools for the project
        supported_providers = await get_supported_tool_providers(project_id)
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
                                "name": "tools-mcp-server",
                                "version": "1.0.0"
                            }
                        }
                    })
                
                elif method == "notifications/initialized":
                    # Handle initialization complete notification
                    logger.info(f"Client initialized for project {project_id}")
                    return JSONResponse(content={}, status_code=200)
                
                elif method == "tools/list":
                    # Return only tools available for this project
                    tools = []
                    
                    # Define full tool schemas for supported tools
                    all_tool_schemas = {
                        # Looker tools
                        "looker_get_models_tool": {
                            "name": "looker_get_models_tool",
                            "description": "Get all Looker models available in the instance",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "looker_get_explores_tool": {
                            "name": "looker_get_explores_tool",
                            "description": "Get all explores for a specific Looker model",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model_name": {"type": "string", "description": "Name of the Looker model"}
                                },
                                "required": ["model_name"]
                            }
                        },
                        "looker_get_dimensions_tool": {
                            "name": "looker_get_dimensions_tool",
                            "description": "Get all dimensions for a specific explore",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model_name": {"type": "string", "description": "Name of the Looker model"},
                                    "explore_name": {"type": "string", "description": "Name of the explore"}
                                },
                                "required": ["model_name", "explore_name"]
                            }
                        },
                        "looker_get_measures_tool": {
                            "name": "looker_get_measures_tool",
                            "description": "Get all measures for a specific explore",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model_name": {"type": "string", "description": "Name of the Looker model"},
                                    "explore_name": {"type": "string", "description": "Name of the explore"}
                                },
                                "required": ["model_name", "explore_name"]
                            }
                        },
                        "looker_get_filters_tool": {
                            "name": "looker_get_filters_tool",
                            "description": "Get all filters for a specific explore",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model_name": {"type": "string", "description": "Name of the Looker model"},
                                    "explore_name": {"type": "string", "description": "Name of the explore"}
                                },
                                "required": ["model_name", "explore_name"]
                            }
                        },
                        "looker_query_tool": {
                            "name": "looker_query_tool",
                            "description": "Execute a Looker query with dimensions, measures, and filters",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model_name": {"type": "string", "description": "Name of the Looker model"},
                                    "explore_name": {"type": "string", "description": "Name of the explore"},
                                    "dimensions": {"type": "array", "items": {"type": "string"}, "description": "List of dimensions"},
                                    "measures": {"type": "array", "items": {"type": "string"}, "description": "List of measures"},
                                    "filters": {"type": "object", "description": "Filter conditions (optional)"},
                                    "limit": {"type": "integer", "description": "Result limit", "default": 100}
                                },
                                "required": ["model_name", "explore_name", "dimensions", "measures"]
                            }
                        },
                        "looker_query_sql_tool": {
                            "name": "looker_query_sql_tool",
                            "description": "Execute raw SQL against Looker's database connection",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sql": {"type": "string", "description": "SQL query to execute"}
                                },
                                "required": ["sql"]
                            }
                        },
                        "looker_get_looks_tool": {
                            "name": "looker_get_looks_tool",
                            "description": "Get all Looks (saved queries) in Looker",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "folder_id": {"type": "string", "description": "Optional folder ID to filter Looks"}
                                },
                                "required": []
                            }
                        },
                        "looker_run_look_tool": {
                            "name": "looker_run_look_tool",
                            "description": "Run a specific Look and get its results",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "look_id": {"type": "string", "description": "Look identifier"},
                                    "limit": {"type": "integer", "description": "Result limit", "default": 100}
                                },
                                "required": ["look_id"]
                            }
                        },
                        "looker_query_url_tool": {
                            "name": "looker_query_url_tool",
                            "description": "Generate a Looker query URL",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model_name": {"type": "string", "description": "Name of the Looker model"},
                                    "explore_name": {"type": "string", "description": "Name of the explore"},
                                    "dimensions": {"type": "array", "items": {"type": "string"}, "description": "List of dimensions"},
                                    "measures": {"type": "array", "items": {"type": "string"}, "description": "List of measures"},
                                    "filters": {"type": "object", "description": "Filter conditions (optional)"}
                                },
                                "required": ["model_name", "explore_name", "dimensions", "measures"]
                            }
                        },
                        
                        # Redash tools
                        "redash_list_queries_tool": {
                            "name": "redash_list_queries_tool",
                            "description": "List all queries in Redash",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "page": {"type": "integer", "description": "Page number", "default": 1},
                                    "page_size": {"type": "integer", "description": "Page size", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "redash_get_query_tool": {
                            "name": "redash_get_query_tool",
                            "description": "Get details of a specific Redash query",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_id": {"type": "string", "description": "Query identifier"}
                                },
                                "required": ["query_id"]
                            }
                        },
                        "redash_execute_query_tool": {
                            "name": "redash_execute_query_tool",
                            "description": "Execute a Redash query and get its results",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_id": {"type": "string", "description": "Query identifier"},
                                    "parameters": {"type": "object", "description": "Query parameters (optional)"}
                                },
                                "required": ["query_id"]
                            }
                        },
                        "redash_get_query_job_status_tool": {
                            "name": "redash_get_query_job_status_tool",
                            "description": "Get the status of a query execution job",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "job_id": {"type": "string", "description": "Job identifier"}
                                },
                                "required": ["job_id"]
                            }
                        },
                        "redash_get_query_results_tool": {
                            "name": "redash_get_query_results_tool",
                            "description": "Get the results of a completed query execution",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_result_id": {"type": "string", "description": "Query result identifier"}
                                },
                                "required": ["query_result_id"]
                            }
                        },
                        "redash_refresh_query_tool": {
                            "name": "redash_refresh_query_tool",
                            "description": "Refresh a Redash query (execute with fresh data)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_id": {"type": "string", "description": "Query identifier"}
                                },
                                "required": ["query_id"]
                            }
                        },
                        "redash_list_dashboards_tool": {
                            "name": "redash_list_dashboards_tool",
                            "description": "List all dashboards in Redash",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "page": {"type": "integer", "description": "Page number", "default": 1},
                                    "page_size": {"type": "integer", "description": "Page size", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "redash_get_dashboard_tool": {
                            "name": "redash_get_dashboard_tool",
                            "description": "Get details of a specific Redash dashboard",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dashboard_id": {"type": "string", "description": "Dashboard identifier"}
                                },
                                "required": ["dashboard_id"]
                            }
                        },
                        "redash_list_data_sources_tool": {
                            "name": "redash_list_data_sources_tool",
                            "description": "List all data sources in Redash",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "redash_create_query_tool": {
                            "name": "redash_create_query_tool",
                            "description": "Create a new query in Redash",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "data_source_id": {"type": "string", "description": "Data source identifier"},
                                    "name": {"type": "string", "description": "Query name"},
                                    "query": {"type": "string", "description": "SQL query text"},
                                    "description": {"type": "string", "description": "Query description (optional)", "default": ""},
                                    "schedule": {"type": "object", "description": "Schedule configuration (optional)"}
                                },
                                "required": ["data_source_id", "name", "query"]
                            }
                        },
                        "redash_create_visualization_tool": {
                            "name": "redash_create_visualization_tool",
                            "description": "Create a new visualization for a query",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query_id": {"type": "string", "description": "Query identifier"},
                                    "viz_type": {"type": "string", "description": "Visualization type (e.g., 'TABLE', 'CHART', 'COUNTER')"},
                                    "name": {"type": "string", "description": "Visualization name"},
                                    "options": {"type": "object", "description": "Visualization options (optional)"},
                                    "description": {"type": "string", "description": "Visualization description (optional)", "default": ""}
                                },
                                "required": ["query_id", "viz_type", "name"]
                            }
                        },
                        "redash_create_dashboard_tool": {
                            "name": "redash_create_dashboard_tool",
                            "description": "Create a new dashboard in Redash",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Dashboard name"}
                                },
                                "required": ["name"]
                            }
                        },
                        "redash_add_widget_tool": {
                            "name": "redash_add_widget_tool",
                            "description": "Add a widget to a dashboard",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dashboard_id": {"type": "string", "description": "Dashboard identifier"},
                                    "visualization_id": {"type": "string", "description": "Visualization identifier (optional)"},
                                    "text": {"type": "string", "description": "Text widget content (optional)"},
                                    "width": {"type": "integer", "description": "Widget width", "default": 1},
                                    "options": {"type": "object", "description": "Widget options (optional)"}
                                },
                                "required": ["dashboard_id"]
                            }
                        },
                        "redash_publish_dashboard_tool": {
                            "name": "redash_publish_dashboard_tool",
                            "description": "Publish a Redash dashboard to make it accessible",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dashboard_id": {"type": "string", "description": "Dashboard identifier"}
                                },
                                "required": ["dashboard_id"]
                            }
                        },

                        # DataZone tools
                        "datazone_list_domains_tool": {
                            "name": "datazone_list_domains_tool",
                            "description": "List all AWS DataZone domains",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "datazone_get_domain_tool": {
                            "name": "datazone_get_domain_tool",
                            "description": "Get details of a specific DataZone domain",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "Domain identifier"}
                                },
                                "required": ["domain_id"]
                            }
                        },
                        "datazone_list_projects_tool": {
                            "name": "datazone_list_projects_tool",
                            "description": "List all projects in a DataZone domain",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 25}
                                },
                                "required": ["domain_id"]
                            }
                        },
                        "datazone_get_project_tool": {
                            "name": "datazone_get_project_tool",
                            "description": "Get details of a specific DataZone project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "datazone_project_id": {"type": "string", "description": "DataZone project identifier"}
                                },
                                "required": ["domain_id", "datazone_project_id"]
                            }
                        },
                        "datazone_search_listings_tool": {
                            "name": "datazone_search_listings_tool",
                            "description": "Search for data assets in DataZone catalog",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "search_text": {"type": "string", "description": "Text to search for", "default": ""},
                                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 25}
                                },
                                "required": ["domain_id"]
                            }
                        },
                        "datazone_get_listing_tool": {
                            "name": "datazone_get_listing_tool",
                            "description": "Get details of a specific data listing",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "listing_id": {"type": "string", "description": "Listing identifier"}
                                },
                                "required": ["domain_id", "listing_id"]
                            }
                        },
                        "datazone_list_environments_tool": {
                            "name": "datazone_list_environments_tool",
                            "description": "List environments in a DataZone project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "datazone_project_id": {"type": "string", "description": "DataZone project identifier"},
                                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 25}
                                },
                                "required": ["domain_id", "datazone_project_id"]
                            }
                        },
                        "datazone_get_environment_tool": {
                            "name": "datazone_get_environment_tool",
                            "description": "Get details of a specific environment",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "environment_id": {"type": "string", "description": "Environment identifier"}
                                },
                                "required": ["domain_id", "environment_id"]
                            }
                        },
                        "datazone_get_asset_tool": {
                            "name": "datazone_get_asset_tool",
                            "description": "Get details of a specific data asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "asset_id": {"type": "string", "description": "Asset identifier"}
                                },
                                "required": ["domain_id", "asset_id"]
                            }
                        },
                        "datazone_list_asset_revisions_tool": {
                            "name": "datazone_list_asset_revisions_tool",
                            "description": "List revisions of a data asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "asset_id": {"type": "string", "description": "Asset identifier"},
                                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 50}
                                },
                                "required": ["domain_id", "asset_id"]
                            }
                        },
                        "datazone_get_glossary_tool": {
                            "name": "datazone_get_glossary_tool",
                            "description": "Get details of a business glossary",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "glossary_id": {"type": "string", "description": "Glossary identifier"}
                                },
                                "required": ["domain_id", "glossary_id"]
                            }
                        },
                        "datazone_get_glossary_term_tool": {
                            "name": "datazone_get_glossary_term_tool",
                            "description": "Get details of a glossary term",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "term_id": {"type": "string", "description": "Glossary term identifier"}
                                },
                                "required": ["domain_id", "term_id"]
                            }
                        },
                        "datazone_create_form_type_tool": {
                            "name": "datazone_create_form_type_tool",
                            "description": "Create a new form type in DataZone",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "name": {"type": "string", "description": "Name of the form type"},
                                    "model": {"type": "string", "description": "JSON string representing the form model structure"},
                                    "owning_project_id": {"type": "string", "description": "DataZone project ID that will own this form type"},
                                    "description": {"type": "string", "description": "Description of the form type", "default": ""},
                                    "status": {"type": "string", "description": "Status of the form type", "default": "ENABLED"}
                                },
                                "required": ["domain_id", "name", "model", "owning_project_id"]
                            }
                        },
                        "datazone_get_form_type_tool": {
                            "name": "datazone_get_form_type_tool",
                            "description": "Get details of a specific form type",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "form_type_id": {"type": "string", "description": "Form type identifier"},
                                    "revision": {"type": "string", "description": "Specific revision to retrieve", "default": ""}
                                },
                                "required": ["domain_id", "form_type_id"]
                            }
                        },
                        "datazone_create_asset_type_tool": {
                            "name": "datazone_create_asset_type_tool",
                            "description": "Create a new asset type in DataZone",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "name": {"type": "string", "description": "Name of the asset type"},
                                    "owning_project_id": {"type": "string", "description": "DataZone project ID that will own this asset type"},
                                    "description": {"type": "string", "description": "Description of the asset type", "default": ""},
                                    "forms_input": {"type": "string", "description": "JSON string representing forms configuration", "default": ""}
                                },
                                "required": ["domain_id", "name", "owning_project_id"]
                            }
                        },
                        "datazone_get_asset_type_tool": {
                            "name": "datazone_get_asset_type_tool",
                            "description": "Get details of a specific asset type",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "asset_type_id": {"type": "string", "description": "Asset type identifier"},
                                    "revision": {"type": "string", "description": "Specific revision to retrieve", "default": ""}
                                },
                                "required": ["domain_id", "asset_type_id"]
                            }
                        },
                        "datazone_list_asset_types_tool": {
                            "name": "datazone_list_asset_types_tool",
                            "description": "List asset types in a DataZone domain",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "domain_id": {"type": "string", "description": "DataZone domain identifier"},
                                    "owning_project_id": {"type": "string", "description": "Filter by owning project ID", "default": ""},
                                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 25}
                                },
                                "required": ["domain_id"]
                            }
                        },

                        # S3 tools
                        "s3_list_buckets_tool": {
                            "name": "s3_list_buckets_tool",
                            "description": "List all S3 buckets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "s3_list_objects_tool": {
                            "name": "s3_list_objects_tool",
                            "description": "List objects in an S3 bucket",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "bucket_name": {"type": "string", "description": "Name of the S3 bucket"},
                                    "prefix": {"type": "string", "description": "Prefix to filter objects", "default": ""},
                                    "max_keys": {"type": "integer", "description": "Maximum number of objects to return", "default": 1000},
                                    "delimiter": {"type": "string", "description": "Delimiter for grouping keys (e.g., '/' for folder structure)", "default": ""}
                                },
                                "required": ["bucket_name"]
                            }
                        },
                        "s3_get_object_tool": {
                            "name": "s3_get_object_tool",
                            "description": "Get an object from S3 with its content and metadata",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "bucket_name": {"type": "string", "description": "Name of the S3 bucket"},
                                    "object_key": {"type": "string", "description": "Key of the object to retrieve"}
                                },
                                "required": ["bucket_name", "object_key"]
                            }
                        },
                        "s3_get_object_metadata_tool": {
                            "name": "s3_get_object_metadata_tool",
                            "description": "Get metadata for an S3 object without downloading the content",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "bucket_name": {"type": "string", "description": "Name of the S3 bucket"},
                                    "object_key": {"type": "string", "description": "Key of the object"}
                                },
                                "required": ["bucket_name", "object_key"]
                            }
                        },
                        "s3_create_bucket_tool": {
                            "name": "s3_create_bucket_tool",
                            "description": "Create a new S3 bucket",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "bucket_name": {"type": "string", "description": "Name of the bucket to create"},
                                    "region": {"type": "string", "description": "AWS region for the bucket (optional)", "default": ""}
                                },
                                "required": ["bucket_name"]
                            }
                        },
                        "s3_put_object_tool": {
                            "name": "s3_put_object_tool",
                            "description": "Upload an object to S3",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "bucket_name": {"type": "string", "description": "Name of the S3 bucket"},
                                    "object_key": {"type": "string", "description": "Key for the object"},
                                    "content": {"type": "string", "description": "Content to upload (text or base64 encoded)"},
                                    "content_type": {"type": "string", "description": "MIME type of the content", "default": ""},
                                    "storage_class": {"type": "string", "description": "Storage class (STANDARD, INTELLIGENT_TIERING, etc.)", "default": "STANDARD"}
                                },
                                "required": ["bucket_name", "object_key", "content"]
                            }
                        },
                        "s3_generate_presigned_url_tool": {
                            "name": "s3_generate_presigned_url_tool",
                            "description": "Generate a presigned URL for S3 object operations (get, put, delete)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "bucket_name": {"type": "string", "description": "Name of the S3 bucket"},
                                    "object_key": {"type": "string", "description": "Key of the object"},
                                    "operation": {"type": "string", "description": "S3 operation (get_object, put_object, delete_object)", "default": "get_object"},
                                    "expiration": {"type": "integer", "description": "URL expiration time in seconds", "default": 3600},
                                    "http_method": {"type": "string", "description": "HTTP method override (GET, PUT, DELETE)", "default": ""}
                                },
                                "required": ["bucket_name", "object_key"]
                            }
                        },
                        "s3_generate_presigned_post_tool": {
                            "name": "s3_generate_presigned_post_tool",
                            "description": "Generate presigned POST data for direct browser uploads to S3",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "bucket_name": {"type": "string", "description": "Name of the S3 bucket"},
                                    "object_key": {"type": "string", "description": "Key for the object to be uploaded"},
                                    "expiration": {"type": "integer", "description": "POST policy expiration time in seconds", "default": 3600}
                                },
                                "required": ["bucket_name", "object_key"]
                            }
                        },

                        # DBT Cloud tools
                        "dbt_list_projects_tool": {
                            "name": "dbt_list_projects_tool",
                            "description": "List all dbt Cloud projects in the account",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "dbt_list_environments_tool": {
                            "name": "dbt_list_environments_tool",
                            "description": "List all environments in a dbt Cloud project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dbt_project_id": {"type": "string", "description": "DBT project identifier (optional)"}
                                },
                                "required": []
                            }
                        },
                        "dbt_list_jobs_tool": {
                            "name": "dbt_list_jobs_tool",
                            "description": "List all jobs in a dbt Cloud project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dbt_project_id": {"type": "string", "description": "DBT project identifier (optional)"}
                                },
                                "required": []
                            }
                        },
                        "dbt_trigger_job_run_tool": {
                            "name": "dbt_trigger_job_run_tool",
                            "description": "Trigger a dbt Cloud job run with optional overrides",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "job_id": {"type": "string", "description": "Job identifier"},
                                    "cause": {"type": "string", "description": "Reason for triggering the job", "default": "API trigger"},
                                    "git_sha": {"type": "string", "description": "Git SHA to run against (optional)"},
                                    "schema_override": {"type": "string", "description": "Schema override (optional)"},
                                    "dbt_version_override": {"type": "string", "description": "dbt version override (optional)"},
                                    "target_name_override": {"type": "string", "description": "Target name override (optional)"},
                                    "generate_docs_override": {"type": "boolean", "description": "Generate docs override (optional)"},
                                    "timeout_seconds_override": {"type": "integer", "description": "Timeout override in seconds (optional)"},
                                    "steps_override": {"type": "array", "items": {"type": "string"}, "description": "List of steps to run (optional)"}
                                },
                                "required": ["job_id"]
                            }
                        },
                        "dbt_get_job_run_tool": {
                            "name": "dbt_get_job_run_tool",
                            "description": "Get details of a specific dbt Cloud job run",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "run_id": {"type": "string", "description": "Run identifier"},
                                    "include_related": {"type": "array", "items": {"type": "string"}, "description": "Related data to include (optional)"}
                                },
                                "required": ["run_id"]
                            }
                        },
                        "dbt_list_job_runs_tool": {
                            "name": "dbt_list_job_runs_tool",
                            "description": "List job runs with optional filters",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "job_id": {"type": "string", "description": "Job identifier (optional)"},
                                    "status": {"type": "string", "description": "Run status filter (optional)"},
                                    "limit": {"type": "integer", "description": "Result limit", "default": 50}
                                },
                                "required": []
                            }
                        },
                        "dbt_cancel_job_run_tool": {
                            "name": "dbt_cancel_job_run_tool",
                            "description": "Cancel a running dbt Cloud job",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "run_id": {"type": "string", "description": "Run identifier"}
                                },
                                "required": ["run_id"]
                            }
                        },
                        "dbt_list_models_tool": {
                            "name": "dbt_list_models_tool",
                            "description": "List all models in a dbt project using Discovery API",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "environment_id": {"type": "string", "description": "Environment identifier (optional)"}
                                },
                                "required": []
                            }
                        },
                        "dbt_get_model_details_tool": {
                            "name": "dbt_get_model_details_tool",
                            "description": "Get detailed information about a specific dbt model",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model_unique_id": {"type": "string", "description": "Model unique identifier"},
                                    "environment_id": {"type": "string", "description": "Environment identifier (optional)"}
                                },
                                "required": ["model_unique_id"]
                            }
                        },
                        "dbt_list_metrics_tool": {
                            "name": "dbt_list_metrics_tool",
                            "description": "List all metrics using dbt Semantic Layer API",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "environment_id": {"type": "string", "description": "Environment identifier (optional)"}
                                },
                                "required": []
                            }
                        },
                        "dbt_query_metrics_tool": {
                            "name": "dbt_query_metrics_tool",
                            "description": "Query metrics using dbt Semantic Layer API",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "metrics": {"type": "array", "items": {"type": "string"}, "description": "List of metrics to query"},
                                    "group_by": {"type": "array", "items": {"type": "string"}, "description": "Dimensions to group by (optional)"},
                                    "where": {"type": "array", "items": {"type": "string"}, "description": "Filter conditions (optional)"},
                                    "order_by": {"type": "array", "items": {"type": "string"}, "description": "Sort order (optional)"},
                                    "limit": {"type": "integer", "description": "Result limit (optional)"},
                                    "environment_id": {"type": "string", "description": "Environment identifier (optional)"}
                                },
                                "required": ["metrics"]
                            }
                        },
                        "dbt_execute_sql_tool": {
                            "name": "dbt_execute_sql_tool",
                            "description": "Execute SQL using dbt Cloud SQL API",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sql": {"type": "string", "description": "SQL query to execute"},
                                    "environment_id": {"type": "string", "description": "Environment identifier (optional)"}
                                },
                                "required": ["sql"]
                            }
                        },
                        
                        # DataHub tools
                        "datahub_search_entities_tool": {
                            "name": "datahub_search_entities_tool",
                            "description": "Search for entities in DataHub",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query string", "default": "*"},
                                    "entity_types": {"type": "array", "items": {"type": "string"}, "description": "List of entity types to filter by (DATASET, CHART, DASHBOARD, etc.)"},
                                    "start": {"type": "integer", "description": "Start index for pagination", "default": 0},
                                    "count": {"type": "integer", "description": "Number of results per page", "default": 10}
                                },
                                "required": []
                            }
                        },
                        "datahub_get_entity_tool": {
                            "name": "datahub_get_entity_tool",
                            "description": "Get details of a specific DataHub entity by URN",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "urn": {"type": "string", "description": "Entity URN to retrieve"}
                                },
                                "required": ["urn"]
                            }
                        },
                        "datahub_get_lineage_tool": {
                            "name": "datahub_get_lineage_tool",
                            "description": "Get lineage information for a DataHub entity",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "urn": {"type": "string", "description": "Entity URN to get lineage for"},
                                    "direction": {"type": "string", "description": "Lineage direction (UPSTREAM or DOWNSTREAM)", "default": "DOWNSTREAM"},
                                    "start": {"type": "integer", "description": "Start index for pagination", "default": 0},
                                    "count": {"type": "integer", "description": "Number of results per page", "default": 100}
                                },
                                "required": ["urn"]
                            }
                        },
                        "datahub_list_datasets_tool": {
                            "name": "datahub_list_datasets_tool",
                            "description": "List datasets in DataHub",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "platform": {"type": "string", "description": "Platform name to filter by (optional)"},
                                    "start": {"type": "integer", "description": "Start index", "default": 0},
                                    "count": {"type": "integer", "description": "Number of results", "default": 20}
                                },
                                "required": []
                            }
                        },
                        "datahub_list_dashboards_tool": {
                            "name": "datahub_list_dashboards_tool",
                            "description": "List dashboards in DataHub",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "integer", "description": "Start index", "default": 0},
                                    "count": {"type": "integer", "description": "Number of results", "default": 20}
                                },
                                "required": []
                            }
                        },
                        "datahub_list_charts_tool": {
                            "name": "datahub_list_charts_tool",
                            "description": "List charts in DataHub",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "integer", "description": "Start index", "default": 0},
                                    "count": {"type": "integer", "description": "Number of results", "default": 20}
                                },
                                "required": []
                            }
                        },
                        "datahub_list_platforms_tool": {
                            "name": "datahub_list_platforms_tool",
                            "description": "List all platforms in DataHub",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "datahub_list_tags_tool": {
                            "name": "datahub_list_tags_tool",
                            "description": "List all tags in DataHub",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "integer", "description": "Start index", "default": 0},
                                    "count": {"type": "integer", "description": "Number of results", "default": 20}
                                },
                                "required": []
                            }
                        },
                        
                        # Airflow tools
                        "airflow_list_dags_tool": {
                            "name": "airflow_list_dags_tool",
                            "description": "List all DAGs in Airflow",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "limit": {"type": "integer", "description": "Result limit", "default": 100},
                                    "offset": {"type": "integer", "description": "Offset for pagination", "default": 0},
                                    "only_active": {"type": "boolean", "description": "Only active DAGs", "default": True}
                                },
                                "required": []
                            }
                        },
                        "airflow_get_dag_tool": {
                            "name": "airflow_get_dag_tool",
                            "description": "Get details of a specific DAG",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dag_id": {"type": "string", "description": "DAG identifier"}
                                },
                                "required": ["dag_id"]
                            }
                        },
                        "airflow_trigger_dag_tool": {
                            "name": "airflow_trigger_dag_tool",
                            "description": "Trigger a DAG run",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dag_id": {"type": "string", "description": "DAG identifier"},
                                    "conf": {"type": "object", "description": "DAG run configuration (optional)"}
                                },
                                "required": ["dag_id"]
                            }
                        },
                        "airflow_get_dag_runs_tool": {
                            "name": "airflow_get_dag_runs_tool",
                            "description": "Get DAG runs for a specific DAG",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dag_id": {"type": "string", "description": "DAG identifier"},
                                    "limit": {"type": "integer", "description": "Result limit", "default": 25},
                                    "offset": {"type": "integer", "description": "Offset for pagination", "default": 0}
                                },
                                "required": ["dag_id"]
                            }
                        },
                        "airflow_get_task_instances_tool": {
                            "name": "airflow_get_task_instances_tool",
                            "description": "Get task instances for a DAG run",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dag_id": {"type": "string", "description": "DAG identifier"},
                                    "dag_run_id": {"type": "string", "description": "DAG run identifier"}
                                },
                                "required": ["dag_id", "dag_run_id"]
                            }
                        },
                        "airflow_get_task_logs_tool": {
                            "name": "airflow_get_task_logs_tool",
                            "description": "Get logs for a task instance",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dag_id": {"type": "string", "description": "DAG identifier"},
                                    "dag_run_id": {"type": "string", "description": "DAG run identifier"},
                                    "task_id": {"type": "string", "description": "Task identifier"},
                                    "task_try_number": {"type": "integer", "description": "Task try number", "default": 1}
                                },
                                "required": ["dag_id", "dag_run_id", "task_id"]
                            }
                        },
                        "airflow_pause_dag_tool": {
                            "name": "airflow_pause_dag_tool",
                            "description": "Pause a DAG",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dag_id": {"type": "string", "description": "DAG identifier"}
                                },
                                "required": ["dag_id"]
                            }
                        },
                        "airflow_unpause_dag_tool": {
                            "name": "airflow_unpause_dag_tool",
                            "description": "Unpause a DAG",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dag_id": {"type": "string", "description": "DAG identifier"}
                                },
                                "required": ["dag_id"]
                            }
                        },
                        
                        # OpenAPI tools
                        "openapi_get_spec_tool": {
                            "name": "openapi_get_spec_tool",
                            "description": "Get the OpenAPI specification for the configured API",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "openapi_list_endpoints_tool": {
                            "name": "openapi_list_endpoints_tool",
                            "description": "List all available API endpoints from OpenAPI spec",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "tag": {"type": "string", "description": "Optional tag to filter endpoints"}
                                },
                                "required": []
                            }
                        },
                        "openapi_call_endpoint_tool": {
                            "name": "openapi_call_endpoint_tool",
                            "description": "Call an API endpoint with specified parameters",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
                                    "path": {"type": "string", "description": "API endpoint path"},
                                    "parameters": {"type": "object", "description": "Request parameters (optional)"},
                                    "data": {"type": "object", "description": "Request body (optional)"},
                                    "headers": {"type": "object", "description": "Request headers (optional)"}
                                },
                                "required": ["method", "path"]
                            }
                        },
                        "openapi_get_endpoint_schema_tool": {
                            "name": "openapi_get_endpoint_schema_tool",
                            "description": "Get the schema definition for a specific endpoint",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "method": {"type": "string", "description": "HTTP method"},
                                    "path": {"type": "string", "description": "API endpoint path"}
                                },
                                "required": ["method", "path"]
                            }
                        },

                        # Jira tools
                        "jira_search_issues_tool": {
                            "name": "jira_search_issues_tool",
                            "description": "Search for Jira issues using JQL (Jira Query Language)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "jql": {"type": "string", "description": "JQL query string"},
                                    "max_results": {"type": "integer", "description": "Maximum number of results (default: 50)"}
                                },
                                "required": ["jql"]
                            }
                        },
                        "jira_get_issue_tool": {
                            "name": "jira_get_issue_tool",
                            "description": "Get details of a specific Jira issue",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key (e.g., 'PROJ-123')"}
                                },
                                "required": ["issue_key"]
                            }
                        },
                        "jira_create_issue_tool": {
                            "name": "jira_create_issue_tool",
                            "description": "Create a new Jira issue",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project_key": {"type": "string", "description": "Project key"},
                                    "summary": {"type": "string", "description": "Issue summary/title"},
                                    "issue_type": {"type": "string", "description": "Issue type (e.g., 'Task', 'Bug', 'Story')"},
                                    "description": {"type": "string", "description": "Issue description (optional)"},
                                    "priority": {"type": "string", "description": "Priority (optional)"},
                                    "assignee_account_id": {"type": "string", "description": "Assignee account ID (optional)"}
                                },
                                "required": ["project_key", "summary", "issue_type"]
                            }
                        },
                        "jira_update_issue_tool": {
                            "name": "jira_update_issue_tool",
                            "description": "Update an existing Jira issue",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key"},
                                    "fields": {"type": "object", "description": "Fields to update"}
                                },
                                "required": ["issue_key", "fields"]
                            }
                        },
                        "jira_transition_issue_tool": {
                            "name": "jira_transition_issue_tool",
                            "description": "Transition a Jira issue to a new status",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key"},
                                    "transition_id": {"type": "string", "description": "Transition ID"}
                                },
                                "required": ["issue_key", "transition_id"]
                            }
                        },
                        "jira_get_transitions_tool": {
                            "name": "jira_get_transitions_tool",
                            "description": "Get available transitions for a Jira issue",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key"}
                                },
                                "required": ["issue_key"]
                            }
                        },
                        "jira_assign_issue_tool": {
                            "name": "jira_assign_issue_tool",
                            "description": "Assign a Jira issue to a user",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key"},
                                    "account_id": {"type": "string", "description": "Atlassian account ID"}
                                },
                                "required": ["issue_key", "account_id"]
                            }
                        },
                        "jira_list_projects_tool": {
                            "name": "jira_list_projects_tool",
                            "description": "List all Jira projects accessible to the user",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "jira_get_project_tool": {
                            "name": "jira_get_project_tool",
                            "description": "Get details of a specific Jira project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project_key": {"type": "string", "description": "Project key"}
                                },
                                "required": ["project_key"]
                            }
                        },
                        "jira_get_issue_types_tool": {
                            "name": "jira_get_issue_types_tool",
                            "description": "Get issue types for a Jira project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project_key": {"type": "string", "description": "Project key"}
                                },
                                "required": ["project_key"]
                            }
                        },
                        "jira_get_fields_tool": {
                            "name": "jira_get_fields_tool",
                            "description": "Get all fields (system and custom) in Jira",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "jira_add_comment_tool": {
                            "name": "jira_add_comment_tool",
                            "description": "Add a comment to a Jira issue",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key"},
                                    "comment": {"type": "string", "description": "Comment text"}
                                },
                                "required": ["issue_key", "comment"]
                            }
                        },
                        "jira_get_comments_tool": {
                            "name": "jira_get_comments_tool",
                            "description": "Get all comments for a Jira issue",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key"}
                                },
                                "required": ["issue_key"]
                            }
                        },
                        "jira_upload_attachment_tool": {
                            "name": "jira_upload_attachment_tool",
                            "description": "Upload an attachment to a Jira issue",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_key": {"type": "string", "description": "Issue key"},
                                    "file_content": {"type": "string", "description": "File content (base64 encoded)"},
                                    "filename": {"type": "string", "description": "Filename"}
                                },
                                "required": ["issue_key", "file_content", "filename"]
                            }
                        },
                        "jira_list_boards_tool": {
                            "name": "jira_list_boards_tool",
                            "description": "List all Jira boards, optionally filtered by project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project_key": {"type": "string", "description": "Optional project key to filter boards"}
                                },
                                "required": []
                            }
                        },
                        "jira_list_sprints_tool": {
                            "name": "jira_list_sprints_tool",
                            "description": "List all sprints for a Jira board",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "board_id": {"type": "integer", "description": "Board ID"}
                                },
                                "required": ["board_id"]
                            }
                        },
                        "jira_get_sprint_tool": {
                            "name": "jira_get_sprint_tool",
                            "description": "Get details of a specific Jira sprint",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sprint_id": {"type": "integer", "description": "Sprint ID"}
                                },
                                "required": ["sprint_id"]
                            }
                        },
                        "jira_get_backlog_tool": {
                            "name": "jira_get_backlog_tool",
                            "description": "Get backlog issues for a Jira board",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "board_id": {"type": "integer", "description": "Board ID"},
                                    "max_results": {"type": "integer", "description": "Maximum number of results (default: 50)"}
                                },
                                "required": ["board_id"]
                            }
                        },

                        # Azure Blob Storage tools
                        "azure_blob_list_containers_tool": {
                            "name": "azure_blob_list_containers_tool",
                            "description": "List all containers in the Azure Blob Storage account",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "max_results": {"type": "integer", "description": "Maximum number of containers to return", "default": 100}
                                },
                                "required": []
                            }
                        },
                        "azure_blob_list_blobs_tool": {
                            "name": "azure_blob_list_blobs_tool",
                            "description": "List blobs in an Azure Blob Storage container",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "container_name": {"type": "string", "description": "Name of the container"},
                                    "prefix": {"type": "string", "description": "Prefix to filter blobs"},
                                    "max_results": {"type": "integer", "description": "Maximum number of blobs to return", "default": 1000},
                                    "delimiter": {"type": "string", "description": "Delimiter for virtual directory structure"}
                                },
                                "required": ["container_name"]
                            }
                        },
                        "azure_blob_get_blob_tool": {
                            "name": "azure_blob_get_blob_tool",
                            "description": "Get a blob from Azure Blob Storage container",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "container_name": {"type": "string", "description": "Name of the container"},
                                    "blob_name": {"type": "string", "description": "Name of the blob to retrieve"}
                                },
                                "required": ["container_name", "blob_name"]
                            }
                        },
                        "azure_blob_get_blob_metadata_tool": {
                            "name": "azure_blob_get_blob_metadata_tool",
                            "description": "Get metadata for a blob without downloading the content",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "container_name": {"type": "string", "description": "Name of the container"},
                                    "blob_name": {"type": "string", "description": "Name of the blob"}
                                },
                                "required": ["container_name", "blob_name"]
                            }
                        },
                        "azure_blob_upload_blob_tool": {
                            "name": "azure_blob_upload_blob_tool",
                            "description": "Upload a blob to Azure Blob Storage container",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "container_name": {"type": "string", "description": "Name of the container"},
                                    "blob_name": {"type": "string", "description": "Name for the blob"},
                                    "content": {"type": "string", "description": "Content to upload"},
                                    "content_type": {"type": "string", "description": "MIME type of the content"},
                                    "overwrite": {"type": "boolean", "description": "Whether to overwrite if blob exists", "default": True}
                                },
                                "required": ["container_name", "blob_name", "content"]
                            }
                        },
                        "azure_blob_delete_blob_tool": {
                            "name": "azure_blob_delete_blob_tool",
                            "description": "Delete a blob from Azure Blob Storage container",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "container_name": {"type": "string", "description": "Name of the container"},
                                    "blob_name": {"type": "string", "description": "Name of the blob to delete"}
                                },
                                "required": ["container_name", "blob_name"]
                            }
                        },
                        "azure_blob_generate_sas_url_tool": {
                            "name": "azure_blob_generate_sas_url_tool",
                            "description": "Generate a SAS (Shared Access Signature) URL for a blob",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "container_name": {"type": "string", "description": "Name of the container"},
                                    "blob_name": {"type": "string", "description": "Name of the blob"},
                                    "expiry_hours": {"type": "integer", "description": "URL expiration time in hours", "default": 1},
                                    "permission": {"type": "string", "description": "Permission string (r=read, w=write, d=delete)", "default": "r"}
                                },
                                "required": ["container_name", "blob_name"]
                            }
                        },
                        "azure_blob_get_container_properties_tool": {
                            "name": "azure_blob_get_container_properties_tool",
                            "description": "Get properties for an Azure Blob Storage container",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "container_name": {"type": "string", "description": "Name of the container"}
                                },
                                "required": ["container_name"]
                            }
                        },

                        # Azure Data Factory tools
                        "azure_adf_list_pipelines_tool": {
                            "name": "azure_adf_list_pipelines_tool",
                            "description": "List all pipelines in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "azure_adf_get_pipeline_tool": {
                            "name": "azure_adf_get_pipeline_tool",
                            "description": "Get details of a specific pipeline in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pipeline_name": {"type": "string", "description": "Name of the pipeline"}
                                },
                                "required": ["pipeline_name"]
                            }
                        },
                        "azure_adf_run_pipeline_tool": {
                            "name": "azure_adf_run_pipeline_tool",
                            "description": "Run a pipeline in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pipeline_name": {"type": "string", "description": "Name of the pipeline"},
                                    "parameters": {"type": "object", "description": "Optional parameters for the pipeline run"}
                                },
                                "required": ["pipeline_name"]
                            }
                        },
                        "azure_adf_get_pipeline_run_tool": {
                            "name": "azure_adf_get_pipeline_run_tool",
                            "description": "Get details of a pipeline run",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "run_id": {"type": "string", "description": "Pipeline run ID"}
                                },
                                "required": ["run_id"]
                            }
                        },
                        "azure_adf_list_pipeline_runs_tool": {
                            "name": "azure_adf_list_pipeline_runs_tool",
                            "description": "List pipeline runs in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pipeline_name": {"type": "string", "description": "Optional: filter by pipeline name"},
                                    "days_back": {"type": "integer", "description": "Number of days to look back", "default": 7}
                                },
                                "required": []
                            }
                        },
                        "azure_adf_list_datasets_tool": {
                            "name": "azure_adf_list_datasets_tool",
                            "description": "List all datasets in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "azure_adf_get_dataset_tool": {
                            "name": "azure_adf_get_dataset_tool",
                            "description": "Get details of a specific dataset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset_name": {"type": "string", "description": "Name of the dataset"}
                                },
                                "required": ["dataset_name"]
                            }
                        },
                        "azure_adf_list_triggers_tool": {
                            "name": "azure_adf_list_triggers_tool",
                            "description": "List all triggers in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "azure_adf_get_trigger_tool": {
                            "name": "azure_adf_get_trigger_tool",
                            "description": "Get details of a specific trigger",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "trigger_name": {"type": "string", "description": "Name of the trigger"}
                                },
                                "required": ["trigger_name"]
                            }
                        },
                        "azure_adf_list_linked_services_tool": {
                            "name": "azure_adf_list_linked_services_tool",
                            "description": "List all linked services in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "azure_adf_get_linked_service_tool": {
                            "name": "azure_adf_get_linked_service_tool",
                            "description": "Get details of a specific linked service",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "service_name": {"type": "string", "description": "Name of the linked service"}
                                },
                                "required": ["service_name"]
                            }
                        },
                        "azure_adf_list_data_flows_tool": {
                            "name": "azure_adf_list_data_flows_tool",
                            "description": "List all data flows in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "azure_adf_get_data_flow_tool": {
                            "name": "azure_adf_get_data_flow_tool",
                            "description": "Get details of a specific data flow",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "data_flow_name": {"type": "string", "description": "Name of the data flow"}
                                },
                                "required": ["data_flow_name"]
                            }
                        },
                        "azure_adf_list_integration_runtimes_tool": {
                            "name": "azure_adf_list_integration_runtimes_tool",
                            "description": "List all integration runtimes in Azure Data Factory",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "azure_adf_get_integration_runtime_tool": {
                            "name": "azure_adf_get_integration_runtime_tool",
                            "description": "Get details of a specific integration runtime",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "runtime_name": {"type": "string", "description": "Name of the integration runtime"}
                                },
                                "required": ["runtime_name"]
                            }
                        },
                        "azure_adf_get_factory_info_tool": {
                            "name": "azure_adf_get_factory_info_tool",
                            "description": "Get information about the Azure Data Factory instance",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        # Atlan tools
                        "atlan_search_assets_tool": {
                            "name": "atlan_search_assets_tool",
                            "description": "Search for assets in Atlan data catalog using Elasticsearch query syntax",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query (Elasticsearch syntax)", "default": "*"},
                                    "asset_types": {"type": "array", "items": {"type": "string"}, "description": "Asset types to filter (Table, Column, Dashboard, etc.)"},
                                    "from_": {"type": "integer", "description": "Pagination offset", "default": 0},
                                    "size": {"type": "integer", "description": "Number of results", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_search_by_type_tool": {
                            "name": "atlan_search_by_type_tool",
                            "description": "Search for all assets of a specific type in Atlan",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "type_name": {"type": "string", "description": "Asset type name (Table, Column, Dashboard, etc.)"},
                                    "from_": {"type": "integer", "description": "Pagination offset", "default": 0},
                                    "size": {"type": "integer", "description": "Number of results", "default": 25}
                                },
                                "required": ["type_name"]
                            }
                        },
                        "atlan_get_asset_tool": {
                            "name": "atlan_get_asset_tool",
                            "description": "Get detailed information about a specific asset by GUID",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"}
                                },
                                "required": ["guid"]
                            }
                        },
                        "atlan_get_asset_by_qualified_name_tool": {
                            "name": "atlan_get_asset_by_qualified_name_tool",
                            "description": "Get asset by type and qualified name",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "type_name": {"type": "string", "description": "Asset type name"},
                                    "qualified_name": {"type": "string", "description": "Asset qualified name"}
                                },
                                "required": ["type_name", "qualified_name"]
                            }
                        },
                        "atlan_create_asset_tool": {
                            "name": "atlan_create_asset_tool",
                            "description": "Create a new asset in Atlan",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "type_name": {"type": "string", "description": "Asset type (Table, Column, etc.)"},
                                    "name": {"type": "string", "description": "Asset display name"},
                                    "qualified_name": {"type": "string", "description": "Unique qualified name"},
                                    "description": {"type": "string", "description": "Asset description"}
                                },
                                "required": ["type_name", "name", "qualified_name"]
                            }
                        },
                        "atlan_update_asset_tool": {
                            "name": "atlan_update_asset_tool",
                            "description": "Update an existing asset in Atlan",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "attributes": {"type": "object", "description": "Attributes to update"}
                                },
                                "required": ["guid", "attributes"]
                            }
                        },
                        "atlan_delete_asset_tool": {
                            "name": "atlan_delete_asset_tool",
                            "description": "Delete an asset from Atlan (soft or hard delete)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "hard_delete": {"type": "boolean", "description": "Permanently delete", "default": False}
                                },
                                "required": ["guid"]
                            }
                        },
                        "atlan_update_asset_description_tool": {
                            "name": "atlan_update_asset_description_tool",
                            "description": "Update the description of an asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "description": {"type": "string", "description": "New description"}
                                },
                                "required": ["guid", "description"]
                            }
                        },
                        "atlan_update_asset_owners_tool": {
                            "name": "atlan_update_asset_owners_tool",
                            "description": "Update the owners of an asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "owner_users": {"type": "array", "items": {"type": "string"}, "description": "Owner usernames"},
                                    "owner_groups": {"type": "array", "items": {"type": "string"}, "description": "Owner group names"}
                                },
                                "required": ["guid"]
                            }
                        },
                        "atlan_get_lineage_tool": {
                            "name": "atlan_get_lineage_tool",
                            "description": "Get lineage information for an asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "direction": {"type": "string", "description": "UPSTREAM, DOWNSTREAM, or BOTH", "default": "BOTH"},
                                    "depth": {"type": "integer", "description": "Lineage depth (1-10)", "default": 3}
                                },
                                "required": ["guid"]
                            }
                        },
                        "atlan_list_glossaries_tool": {
                            "name": "atlan_list_glossaries_tool",
                            "description": "List all glossaries in Atlan",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_get_glossary_tool": {
                            "name": "atlan_get_glossary_tool",
                            "description": "Get a specific glossary by GUID",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Glossary GUID"}
                                },
                                "required": ["guid"]
                            }
                        },
                        "atlan_list_glossary_terms_tool": {
                            "name": "atlan_list_glossary_terms_tool",
                            "description": "List glossary terms, optionally filtered by glossary",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "glossary_guid": {"type": "string", "description": "Glossary GUID to filter by"},
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_get_glossary_term_tool": {
                            "name": "atlan_get_glossary_term_tool",
                            "description": "Get a specific glossary term by GUID",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Term GUID"}
                                },
                                "required": ["guid"]
                            }
                        },
                        "atlan_create_glossary_term_tool": {
                            "name": "atlan_create_glossary_term_tool",
                            "description": "Create a new glossary term",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Term name"},
                                    "glossary_guid": {"type": "string", "description": "Parent glossary GUID"},
                                    "description": {"type": "string", "description": "Term description"},
                                    "short_description": {"type": "string", "description": "Short description"}
                                },
                                "required": ["name", "glossary_guid"]
                            }
                        },
                        "atlan_list_glossary_categories_tool": {
                            "name": "atlan_list_glossary_categories_tool",
                            "description": "List glossary categories",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "glossary_guid": {"type": "string", "description": "Glossary GUID to filter by"},
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_link_term_to_asset_tool": {
                            "name": "atlan_link_term_to_asset_tool",
                            "description": "Link a glossary term to an asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "term_guid": {"type": "string", "description": "Glossary term GUID"},
                                    "asset_guid": {"type": "string", "description": "Asset GUID to link to"}
                                },
                                "required": ["term_guid", "asset_guid"]
                            }
                        },
                        "atlan_list_classifications_tool": {
                            "name": "atlan_list_classifications_tool",
                            "description": "List all classification types (tags) in Atlan",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "atlan_add_classification_tool": {
                            "name": "atlan_add_classification_tool",
                            "description": "Add a classification (tag) to an asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "classification_name": {"type": "string", "description": "Classification type name"}
                                },
                                "required": ["guid", "classification_name"]
                            }
                        },
                        "atlan_remove_classification_tool": {
                            "name": "atlan_remove_classification_tool",
                            "description": "Remove a classification from an asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "classification_name": {"type": "string", "description": "Classification type name"}
                                },
                                "required": ["guid", "classification_name"]
                            }
                        },
                        "atlan_list_tables_tool": {
                            "name": "atlan_list_tables_tool",
                            "description": "List all table assets in Atlan",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_columns_tool": {
                            "name": "atlan_list_columns_tool",
                            "description": "List columns, optionally filtered by parent table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_guid": {"type": "string", "description": "Parent table GUID"},
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_databases_tool": {
                            "name": "atlan_list_databases_tool",
                            "description": "List all database assets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_schemas_tool": {
                            "name": "atlan_list_schemas_tool",
                            "description": "List all schema assets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_dashboards_tool": {
                            "name": "atlan_list_dashboards_tool",
                            "description": "List all BI dashboard assets (Tableau, Looker, PowerBI, etc.)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_dbt_models_tool": {
                            "name": "atlan_list_dbt_models_tool",
                            "description": "List dbt model assets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_airflow_dags_tool": {
                            "name": "atlan_list_airflow_dags_tool",
                            "description": "List Airflow DAG assets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_kafka_topics_tool": {
                            "name": "atlan_list_kafka_topics_tool",
                            "description": "List Kafka topic assets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_list_s3_objects_tool": {
                            "name": "atlan_list_s3_objects_tool",
                            "description": "List S3 and cloud storage assets",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "from_": {"type": "integer", "default": 0},
                                    "size": {"type": "integer", "default": 25}
                                },
                                "required": []
                            }
                        },
                        "atlan_update_custom_metadata_tool": {
                            "name": "atlan_update_custom_metadata_tool",
                            "description": "Update custom metadata on an asset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "custom_metadata_name": {"type": "string", "description": "Custom metadata type name"},
                                    "attributes": {"type": "object", "description": "Attribute values to set"}
                                },
                                "required": ["guid", "custom_metadata_name", "attributes"]
                            }
                        },
                        "atlan_get_custom_metadata_types_tool": {
                            "name": "atlan_get_custom_metadata_types_tool",
                            "description": "Get all custom metadata type definitions",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "atlan_certify_asset_tool": {
                            "name": "atlan_certify_asset_tool",
                            "description": "Certify an asset with a status",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guid": {"type": "string", "description": "Asset GUID"},
                                    "status": {"type": "string", "description": "VERIFIED, DEPRECATED, or DRAFT", "default": "VERIFIED"},
                                    "message": {"type": "string", "description": "Certification message"}
                                },
                                "required": ["guid"]
                            }
                        },
                        "atlan_bulk_update_assets_tool": {
                            "name": "atlan_bulk_update_assets_tool",
                            "description": "Update multiple assets in a single request",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "entities": {"type": "array", "items": {"type": "object"}, "description": "Array of entity objects to update"}
                                },
                                "required": ["entities"]
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
                    
                    # Inject project_id into tool arguments
                    tool_arguments["project_id"] = project_id
                    
                    # Map tool names to their actual functions
                    tool_functions = {
                        # Looker tools
                        "looker_get_models_tool": looker_get_models_tool,
                        "looker_get_explores_tool": looker_get_explores_tool,
                        "looker_get_dimensions_tool": looker_get_dimensions_tool,
                        "looker_get_measures_tool": looker_get_measures_tool,
                        "looker_get_filters_tool": looker_get_filters_tool,
                        "looker_query_tool": looker_query_tool,
                        "looker_query_sql_tool": looker_query_sql_tool,
                        "looker_get_looks_tool": looker_get_looks_tool,
                        "looker_run_look_tool": looker_run_look_tool,
                        "looker_query_url_tool": looker_query_url_tool,
                        # Redash tools
                        "redash_list_queries_tool": redash_list_queries_tool,
                        "redash_get_query_tool": redash_get_query_tool,
                        "redash_execute_query_tool": redash_execute_query_tool,
                        "redash_get_query_job_status_tool": redash_get_query_job_status_tool,
                        "redash_get_query_results_tool": redash_get_query_results_tool,
                        "redash_refresh_query_tool": redash_refresh_query_tool,
                        "redash_list_dashboards_tool": redash_list_dashboards_tool,
                        "redash_get_dashboard_tool": redash_get_dashboard_tool,
                        "redash_list_data_sources_tool": redash_list_data_sources_tool,
                        "redash_create_query_tool": redash_create_query_tool,
                        "redash_create_visualization_tool": redash_create_visualization_tool,
                        "redash_create_dashboard_tool": redash_create_dashboard_tool,
                        "redash_add_widget_tool": redash_add_widget_tool,
                        "redash_publish_dashboard_tool": redash_publish_dashboard_tool,
                        # DataZone tools
                        "datazone_list_domains_tool": datazone_list_domains_tool,
                        "datazone_get_domain_tool": datazone_get_domain_tool,
                        "datazone_list_projects_tool": datazone_list_projects_tool,
                        "datazone_get_project_tool": datazone_get_project_tool,
                        "datazone_search_listings_tool": datazone_search_listings_tool,
                        "datazone_get_listing_tool": datazone_get_listing_tool,
                        "datazone_list_environments_tool": datazone_list_environments_tool,
                        "datazone_get_environment_tool": datazone_get_environment_tool,
                        "datazone_get_asset_tool": datazone_get_asset_tool,
                        "datazone_list_asset_revisions_tool": datazone_list_asset_revisions_tool,
                        "datazone_get_glossary_tool": datazone_get_glossary_tool,
                        "datazone_get_glossary_term_tool": datazone_get_glossary_term_tool,
                        "datazone_create_form_type_tool": datazone_create_form_type_tool,
                        "datazone_get_form_type_tool": datazone_get_form_type_tool,
                        "datazone_create_asset_type_tool": datazone_create_asset_type_tool,
                        "datazone_get_asset_type_tool": datazone_get_asset_type_tool,
                        "datazone_list_asset_types_tool": datazone_list_asset_types_tool,
                        # S3 tools
                        "s3_list_buckets_tool": s3_list_buckets_tool,
                        "s3_list_objects_tool": s3_list_objects_tool,
                        "s3_get_object_tool": s3_get_object_tool,
                        "s3_get_object_metadata_tool": s3_get_object_metadata_tool,
                        "s3_create_bucket_tool": s3_create_bucket_tool,
                        "s3_put_object_tool": s3_put_object_tool,
                        "s3_generate_presigned_url_tool": s3_generate_presigned_url_tool,
                        "s3_generate_presigned_post_tool": s3_generate_presigned_post_tool,
                        # DBT tools
                        "dbt_list_projects_tool": dbt_list_projects_tool,
                        "dbt_list_environments_tool": dbt_list_environments_tool,
                        "dbt_list_jobs_tool": dbt_list_jobs_tool,
                        "dbt_trigger_job_run_tool": dbt_trigger_job_run_tool,
                        "dbt_get_job_run_tool": dbt_get_job_run_tool,
                        "dbt_list_job_runs_tool": dbt_list_job_runs_tool,
                        "dbt_cancel_job_run_tool": dbt_cancel_job_run_tool,
                        "dbt_list_models_tool": dbt_list_models_tool,
                        "dbt_get_model_details_tool": dbt_get_model_details_tool,
                        "dbt_list_metrics_tool": dbt_list_metrics_tool,
                        "dbt_query_metrics_tool": dbt_query_metrics_tool,
                        "dbt_execute_sql_tool": dbt_execute_sql_tool,
                        # DataHub tools
                        "datahub_search_entities_tool": datahub_search_entities_tool,
                        "datahub_get_entity_tool": datahub_get_entity_tool,
                        "datahub_list_datasets_tool": datahub_list_datasets_tool,
                        "datahub_list_dashboards_tool": datahub_list_dashboards_tool,
                        "datahub_list_charts_tool": datahub_list_charts_tool,
                        "datahub_get_lineage_tool": datahub_get_lineage_tool,
                        "datahub_list_platforms_tool": datahub_list_platforms_tool,
                        "datahub_list_tags_tool": datahub_list_tags_tool,
                        # Atlan tools
                        "atlan_search_assets_tool": atlan_search_assets_tool,
                        "atlan_search_by_type_tool": atlan_search_by_type_tool,
                        "atlan_get_asset_tool": atlan_get_asset_tool,
                        "atlan_get_asset_by_qualified_name_tool": atlan_get_asset_by_qualified_name_tool,
                        "atlan_create_asset_tool": atlan_create_asset_tool,
                        "atlan_update_asset_tool": atlan_update_asset_tool,
                        "atlan_delete_asset_tool": atlan_delete_asset_tool,
                        "atlan_update_asset_description_tool": atlan_update_asset_description_tool,
                        "atlan_update_asset_owners_tool": atlan_update_asset_owners_tool,
                        "atlan_get_lineage_tool": atlan_get_lineage_tool,
                        "atlan_list_glossaries_tool": atlan_list_glossaries_tool,
                        "atlan_get_glossary_tool": atlan_get_glossary_tool,
                        "atlan_list_glossary_terms_tool": atlan_list_glossary_terms_tool,
                        "atlan_get_glossary_term_tool": atlan_get_glossary_term_tool,
                        "atlan_create_glossary_term_tool": atlan_create_glossary_term_tool,
                        "atlan_list_glossary_categories_tool": atlan_list_glossary_categories_tool,
                        "atlan_link_term_to_asset_tool": atlan_link_term_to_asset_tool,
                        "atlan_list_classifications_tool": atlan_list_classifications_tool,
                        "atlan_add_classification_tool": atlan_add_classification_tool,
                        "atlan_remove_classification_tool": atlan_remove_classification_tool,
                        "atlan_list_tables_tool": atlan_list_tables_tool,
                        "atlan_list_columns_tool": atlan_list_columns_tool,
                        "atlan_list_databases_tool": atlan_list_databases_tool,
                        "atlan_list_schemas_tool": atlan_list_schemas_tool,
                        "atlan_list_dashboards_tool": atlan_list_dashboards_tool,
                        "atlan_list_dbt_models_tool": atlan_list_dbt_models_tool,
                        "atlan_list_airflow_dags_tool": atlan_list_airflow_dags_tool,
                        "atlan_list_kafka_topics_tool": atlan_list_kafka_topics_tool,
                        "atlan_list_s3_objects_tool": atlan_list_s3_objects_tool,
                        "atlan_update_custom_metadata_tool": atlan_update_custom_metadata_tool,
                        "atlan_get_custom_metadata_types_tool": atlan_get_custom_metadata_types_tool,
                        "atlan_certify_asset_tool": atlan_certify_asset_tool,
                        "atlan_bulk_update_assets_tool": atlan_bulk_update_assets_tool,
                        # Airflow tools
                        "airflow_list_dags_tool": airflow_list_dags_tool,
                        "airflow_get_dag_tool": airflow_get_dag_tool,
                        "airflow_trigger_dag_tool": airflow_trigger_dag_tool,
                        "airflow_get_dag_runs_tool": airflow_get_dag_runs_tool,
                        "airflow_get_task_instances_tool": airflow_get_task_instances_tool,
                        "airflow_get_task_logs_tool": airflow_get_task_logs_tool,
                        "airflow_pause_dag_tool": airflow_pause_dag_tool,
                        "airflow_unpause_dag_tool": airflow_unpause_dag_tool,
                        # OpenAPI tools
                        "openapi_get_spec_tool": openapi_get_spec_tool,
                        "openapi_list_endpoints_tool": openapi_list_endpoints_tool,
                        "openapi_call_endpoint_tool": openapi_call_endpoint_tool,
                        "openapi_get_endpoint_schema_tool": openapi_get_endpoint_schema_tool,
                        # Jira tools
                        "jira_search_issues_tool": jira_search_issues_tool,
                        "jira_get_issue_tool": jira_get_issue_tool,
                        "jira_create_issue_tool": jira_create_issue_tool,
                        "jira_update_issue_tool": jira_update_issue_tool,
                        "jira_transition_issue_tool": jira_transition_issue_tool,
                        "jira_get_transitions_tool": jira_get_transitions_tool,
                        "jira_assign_issue_tool": jira_assign_issue_tool,
                        "jira_list_projects_tool": jira_list_projects_tool,
                        "jira_get_project_tool": jira_get_project_tool,
                        "jira_get_issue_types_tool": jira_get_issue_types_tool,
                        "jira_get_fields_tool": jira_get_fields_tool,
                        "jira_add_comment_tool": jira_add_comment_tool,
                        "jira_get_comments_tool": jira_get_comments_tool,
                        "jira_upload_attachment_tool": jira_upload_attachment_tool,
                        "jira_list_boards_tool": jira_list_boards_tool,
                        "jira_list_sprints_tool": jira_list_sprints_tool,
                        "jira_get_sprint_tool": jira_get_sprint_tool,
                        "jira_get_backlog_tool": jira_get_backlog_tool,
                        # Azure Blob Storage tools
                        "azure_blob_list_containers_tool": azure_blob_list_containers_tool,
                        "azure_blob_list_blobs_tool": azure_blob_list_blobs_tool,
                        "azure_blob_get_blob_tool": azure_blob_get_blob_tool,
                        "azure_blob_get_blob_metadata_tool": azure_blob_get_blob_metadata_tool,
                        "azure_blob_upload_blob_tool": azure_blob_upload_blob_tool,
                        "azure_blob_delete_blob_tool": azure_blob_delete_blob_tool,
                        "azure_blob_generate_sas_url_tool": azure_blob_generate_sas_url_tool,
                        "azure_blob_get_container_properties_tool": azure_blob_get_container_properties_tool,
                        # Azure Data Factory tools
                        "azure_adf_list_pipelines_tool": azure_adf_list_pipelines_tool,
                        "azure_adf_get_pipeline_tool": azure_adf_get_pipeline_tool,
                        "azure_adf_run_pipeline_tool": azure_adf_run_pipeline_tool,
                        "azure_adf_get_pipeline_run_tool": azure_adf_get_pipeline_run_tool,
                        "azure_adf_list_pipeline_runs_tool": azure_adf_list_pipeline_runs_tool,
                        "azure_adf_list_datasets_tool": azure_adf_list_datasets_tool,
                        "azure_adf_get_dataset_tool": azure_adf_get_dataset_tool,
                        "azure_adf_list_triggers_tool": azure_adf_list_triggers_tool,
                        "azure_adf_get_trigger_tool": azure_adf_get_trigger_tool,
                        "azure_adf_list_linked_services_tool": azure_adf_list_linked_services_tool,
                        "azure_adf_get_linked_service_tool": azure_adf_get_linked_service_tool,
                        "azure_adf_list_data_flows_tool": azure_adf_list_data_flows_tool,
                        "azure_adf_get_data_flow_tool": azure_adf_get_data_flow_tool,
                        "azure_adf_list_integration_runtimes_tool": azure_adf_list_integration_runtimes_tool,
                        "azure_adf_get_integration_runtime_tool": azure_adf_get_integration_runtime_tool,
                        "azure_adf_get_factory_info_tool": azure_adf_get_factory_info_tool
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

                        # Log tool execution start
                        # Sanitize arguments to avoid logging sensitive data
                        sanitized_args = {k: v for k, v in tool_arguments.items() if k not in ['api_key', 'password', 'token', 'secret']}
                        logger.info(f"Executing tool '{tool_name}' for project '{project_id}' with args: {sanitized_args}")

                        # Call the tool function with injected project_id and measure execution time
                        start_time = time.time()
                        result = await tool_func(**tool_arguments)
                        execution_time = time.time() - start_time

                        # Log successful completion
                        logger.info(f"Tool '{tool_name}' completed successfully in {execution_time:.2f}s")

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
                        logger.error(f"Error executing tool '{tool_name}' for project '{project_id}': {e}", exc_info=True)
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


# =============================================================================
# SERVER SETUP
# =============================================================================

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
            "server": "tools-mcp-server",
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


async def cleanup():
    """Cleanup resources on server shutdown."""
    logger.info("Cleaning up tools connections...")
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

    logger.info("Starting Tools MCP Server on 0.0.0.0:8080")

    # Run the FastMCP server with HTTP transport (streamable)
    mcp.run(transport="streamable-http")

import os
import sys

from services.customer.personalization import get_project_config
from services.training.utils.databricks_metadata_generator import generate_databricks_overview
from services.utils.logger import logger


def run(config):
    """Main entry point for Databricks scanning task"""
    logger.info("Starting Databricks scanning task...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Get Databricks configuration from environment
    databricks_access_token = os.getenv(f"{project.upper()}_DATABRICKS_ACCESS_TOKEN",
                                       os.getenv("DATABRICKS_ACCESS_TOKEN", None))
    databricks_server_hostname = os.getenv(f"{project.upper()}_DATABRICKS_HOST",
                                          os.getenv("DATABRICKS_HOST", None))
    databricks_http_path = os.getenv(f"{project.upper()}_DATABRICKS_HTTP_PATH",
                                    os.getenv("DATABRICKS_HTTP_PATH", None))
    
    schema = os.getenv(f"{project.upper()}_DATABRICKS_SCHEMA", os.getenv("DATABRICKS_SCHEMA", None))
    catalog = os.getenv(f"{project.upper()}_DATABRICKS_CATALOG", os.getenv("DATABRICKS_CATALOG", None))

    # Check for required Databricks configuration
    if not databricks_access_token:
        logger.info("No Databricks access token found - skipping Databricks scanning")
        return None
        
    if not databricks_server_hostname:
        logger.error("DATABRICKS_SERVER_HOSTNAME not found - required for connection")
        return None
        
    if not databricks_http_path:
        logger.warning("DATABRICKS_HTTP_PATH not found - using default")
        databricks_http_path = "/sql/1.0/warehouses/default"

    # Build Databricks connection info
    databricks_config = {
        "access_token": databricks_access_token,
        "server_hostname": databricks_server_hostname,
        "http_path": databricks_http_path
    }
    
    # Parse target catalogs and schemas from environment
    target_catalogs = None
    if catalog:
        target_catalogs = [cat.strip() for cat in catalog.split(',')]
        logger.info(f"Target catalogs from environment: {target_catalogs}")

    target_schemas = None
    if schema:
        target_schemas = [sch.strip() for sch in schema.split(',')]
        logger.info(f"Target schemas from environment: {target_schemas}")

    # Set destination folder for metadata
    dest_folder = f'{base_dir}/{project}/raw/data'
    
    try:
        logger.info(f"Processing Databricks metadata for project: {project}")
        
        # Generate Databricks metadata using the same pattern as BigQuery
        generate_databricks_overview(
            base_dir,
            project_config,
            dest_folder,
            target_catalogs=target_catalogs,
            target_schemas=target_schemas,
            databricks_config=databricks_config,
            output_format="json"
        )
        
        logger.info(f"✓ Databricks scanning completed successfully for project: {project}")
        
    except Exception as e:
        logger.error(f"✗ Databricks scanning failed for project: {project}")
        logger.error(f"Error details: {str(e)}", exc_info=True)
        raise

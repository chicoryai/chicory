import os
import sys

from services.customer.personalization import get_project_config
from services.utils.logger import logger
from services.training.utils.atlan_metadata_generator import generate_atlan_overview


def run(config):
    """Main entry point for Atlan scanning task"""
    logger.info("Starting Atlan data catalog scanning task...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Get Atlan configuration from environment
    atlan_tenant_url = os.getenv(f"{project.upper()}_ATLAN_TENANT_URL",
                                 os.getenv("ATLAN_TENANT_URL", None))
    atlan_api_token = os.getenv(f"{project.upper()}_ATLAN_API_TOKEN",
                                os.getenv("ATLAN_API_TOKEN", None))

    # Optional configuration
    atlan_max_assets = int(os.getenv(f"{project.upper()}_ATLAN_MAX_ASSETS",
                                     os.getenv("ATLAN_MAX_ASSETS", "10000")))
    atlan_include_lineage = os.getenv(f"{project.upper()}_ATLAN_INCLUDE_LINEAGE",
                                      os.getenv("ATLAN_INCLUDE_LINEAGE", "true")).lower() == "true"
    atlan_include_glossary = os.getenv(f"{project.upper()}_ATLAN_INCLUDE_GLOSSARY",
                                       os.getenv("ATLAN_INCLUDE_GLOSSARY", "true")).lower() == "true"
    atlan_asset_types = os.getenv(f"{project.upper()}_ATLAN_ASSET_TYPES",
                                  os.getenv("ATLAN_ASSET_TYPES", None))

    # Check for required Atlan configuration
    if not atlan_tenant_url:
        logger.info("No Atlan tenant URL found - skipping Atlan scanning")
        return None

    if not atlan_api_token:
        logger.error("ATLAN_API_TOKEN not found - required for authentication")
        return None

    # Parse target asset types from environment variable
    target_asset_types = None
    if atlan_asset_types:
        target_asset_types = [t.strip() for t in atlan_asset_types.split(',')]
        logger.info(f"Target asset types from environment: {target_asset_types}")

    # Build Atlan connection config
    atlan_config = {
        "tenant_url": atlan_tenant_url.rstrip('/'),
        "api_token": atlan_api_token,
        "max_assets": atlan_max_assets,
        "include_lineage": atlan_include_lineage,
        "include_glossary": atlan_include_glossary
    }

    # Set destination folder for metadata
    dest_folder = f'{base_dir}/{project}/raw/data'

    try:
        logger.info(f"Processing Atlan metadata for project: {project}")
        logger.info(f"Atlan tenant: {atlan_tenant_url}")
        logger.info(f"Max assets: {atlan_max_assets}, Include lineage: {atlan_include_lineage}, Include glossary: {atlan_include_glossary}")

        # Generate Atlan metadata
        generate_atlan_overview(
            base_dir,
            project_config,
            dest_folder,
            target_asset_types=target_asset_types,
            atlan_config=atlan_config,
            output_format="json"
        )

        logger.info(f"Atlan scanning completed successfully for project: {project}")

    except Exception as e:
        logger.error(f"Atlan scanning failed for project: {project}")
        logger.error(f"Error details: {str(e)}", exc_info=True)
        raise

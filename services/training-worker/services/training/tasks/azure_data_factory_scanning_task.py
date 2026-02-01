"""
Azure Data Factory scanning task for metadata extraction.
Uses Azure AD Service Principal authentication.
"""

import os

from services.customer.personalization import get_project_config
from services.utils.logger import logger
from services.training.utils.azure_data_factory_metadata_generator import generate_azure_data_factory_overview


def run(config):
    """
    Azure Data Factory scanning task entry point.

    Config keys:
        - PROJECT: Project name
        - BASE_DIR: Base directory for output
        - AZURE_ADF_TENANT_ID or {PROJECT}_AZURE_ADF_TENANT_ID
        - AZURE_ADF_CLIENT_ID or {PROJECT}_AZURE_ADF_CLIENT_ID
        - AZURE_ADF_CLIENT_SECRET or {PROJECT}_AZURE_ADF_CLIENT_SECRET
        - AZURE_ADF_SUBSCRIPTION_ID or {PROJECT}_AZURE_ADF_SUBSCRIPTION_ID
        - AZURE_ADF_RESOURCE_GROUP or {PROJECT}_AZURE_ADF_RESOURCE_GROUP
        - AZURE_ADF_FACTORY_NAME or {PROJECT}_AZURE_ADF_FACTORY_NAME
        - AZURE_ADF_DAYS_BACK (optional, for execution history, default: 7)
    """
    logger.info("Analyzing for Azure Data Factory...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Fetch Azure Data Factory connection details from environment
    # Using Azure AD Service Principal authentication
    azure_tenant_id = os.getenv(f"{project.upper()}_AZURE_ADF_TENANT_ID",
                                 os.getenv("AZURE_ADF_TENANT_ID", None))
    azure_client_id = os.getenv(f"{project.upper()}_AZURE_ADF_CLIENT_ID",
                                 os.getenv("AZURE_ADF_CLIENT_ID", None))
    azure_client_secret = os.getenv(f"{project.upper()}_AZURE_ADF_CLIENT_SECRET",
                                     os.getenv("AZURE_ADF_CLIENT_SECRET", None))
    azure_subscription_id = os.getenv(f"{project.upper()}_AZURE_ADF_SUBSCRIPTION_ID",
                                       os.getenv("AZURE_ADF_SUBSCRIPTION_ID", None))
    azure_resource_group = os.getenv(f"{project.upper()}_AZURE_ADF_RESOURCE_GROUP",
                                      os.getenv("AZURE_ADF_RESOURCE_GROUP", None))
    azure_factory_name = os.getenv(f"{project.upper()}_AZURE_ADF_FACTORY_NAME",
                                    os.getenv("AZURE_ADF_FACTORY_NAME", None))
    azure_days_back = os.getenv(f"{project.upper()}_AZURE_ADF_DAYS_BACK",
                                 os.getenv("AZURE_ADF_DAYS_BACK", "7"))

    # Check if we have the required credentials
    required_creds = [azure_tenant_id, azure_client_id, azure_client_secret,
                      azure_subscription_id, azure_resource_group, azure_factory_name]

    if all(required_creds):
        # tabular data
        dest_folder = f'{base_dir}/{project}/raw/data'
        logger.info(f"Using Azure Data Factory: {azure_factory_name} in resource group: {azure_resource_group}")

        try:
            logger.info("Generating Azure Data Factory overview...")

            # Parse days back for execution history
            try:
                days_back = int(azure_days_back)
            except ValueError:
                days_back = 7

            # Create Azure ADF configuration for the generator
            azure_adf_config = {
                "tenant_id": azure_tenant_id,
                "client_id": azure_client_id,
                "client_secret": azure_client_secret,
                "subscription_id": azure_subscription_id,
                "resource_group": azure_resource_group,
                "factory_name": azure_factory_name
            }

            generate_azure_data_factory_overview(
                base_dir,
                project,
                dest_folder,
                azure_adf_config,
                days_back=days_back,
                output_format="json"
            )

            logger.info(f"Scanning Azure Data Factory completed for project: {project}")

        except Exception as e:
            logger.error(f"Scanning Azure Data Factory failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info("No Azure Data Factory Integration Found!")

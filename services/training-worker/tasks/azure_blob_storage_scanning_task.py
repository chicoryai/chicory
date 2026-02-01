"""
Azure Blob Storage scanning task for metadata extraction.
Uses Azure AD Service Principal authentication.
"""

import os

from services.customer.personalization import get_project_config
from services.utils.logger import logger
from services.training.utils.azure_blob_storage_metadata_generator import generate_azure_blob_storage_overview


def run(config):
    """
    Azure Blob Storage scanning task entry point.

    Config keys:
        - PROJECT: Project name
        - BASE_DIR: Base directory for output
        - AZURE_BLOB_TENANT_ID or {PROJECT}_AZURE_BLOB_TENANT_ID
        - AZURE_BLOB_CLIENT_ID or {PROJECT}_AZURE_BLOB_CLIENT_ID
        - AZURE_BLOB_CLIENT_SECRET or {PROJECT}_AZURE_BLOB_CLIENT_SECRET
        - AZURE_BLOB_SUBSCRIPTION_ID or {PROJECT}_AZURE_BLOB_SUBSCRIPTION_ID
        - AZURE_BLOB_STORAGE_ACCOUNT or {PROJECT}_AZURE_BLOB_STORAGE_ACCOUNT
        - AZURE_BLOB_TARGET_CONTAINERS (optional, comma-separated)
        - AZURE_BLOB_MAX_BLOBS_PER_CONTAINER (optional, default: 1000)
    """
    logger.info("Analyzing for Azure Blob Storage...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Fetch Azure Blob Storage connection details from environment
    # Using Azure AD Service Principal authentication
    azure_tenant_id = os.getenv(f"{project.upper()}_AZURE_BLOB_TENANT_ID",
                                 os.getenv("AZURE_BLOB_TENANT_ID", None))
    azure_client_id = os.getenv(f"{project.upper()}_AZURE_BLOB_CLIENT_ID",
                                 os.getenv("AZURE_BLOB_CLIENT_ID", None))
    azure_client_secret = os.getenv(f"{project.upper()}_AZURE_BLOB_CLIENT_SECRET",
                                     os.getenv("AZURE_BLOB_CLIENT_SECRET", None))
    azure_subscription_id = os.getenv(f"{project.upper()}_AZURE_BLOB_SUBSCRIPTION_ID",
                                       os.getenv("AZURE_BLOB_SUBSCRIPTION_ID", None))
    azure_storage_account = os.getenv(f"{project.upper()}_AZURE_BLOB_STORAGE_ACCOUNT",
                                       os.getenv("AZURE_BLOB_STORAGE_ACCOUNT", None))
    azure_target_containers = os.getenv(f"{project.upper()}_AZURE_BLOB_TARGET_CONTAINERS",
                                         os.getenv("AZURE_BLOB_TARGET_CONTAINERS", None))
    azure_max_blobs = os.getenv(f"{project.upper()}_AZURE_BLOB_MAX_BLOBS_PER_CONTAINER",
                                 os.getenv("AZURE_BLOB_MAX_BLOBS_PER_CONTAINER", "1000"))

    # Check if we have the required credentials
    required_creds = [azure_tenant_id, azure_client_id, azure_client_secret, azure_storage_account]

    if all(required_creds):
        # tabular data
        dest_folder = f'{base_dir}/{project}/raw/data'
        logger.info(f"Using Azure Blob Storage account: {azure_storage_account}")

        try:
            logger.info("Generating Azure Blob Storage overview...")

            # Parse target containers from environment variable
            target_containers = None
            if azure_target_containers:
                # Parse comma-separated list from environment variable
                target_containers = [c.strip() for c in azure_target_containers.split(',')]
                logger.info(f"Target containers from environment: {target_containers}")

            # Parse max blobs per container
            try:
                max_blobs_per_container = int(azure_max_blobs)
            except ValueError:
                max_blobs_per_container = 1000

            # Create Azure configuration for the generator
            azure_config = {
                "tenant_id": azure_tenant_id,
                "client_id": azure_client_id,
                "client_secret": azure_client_secret,
                "subscription_id": azure_subscription_id,
                "storage_account_name": azure_storage_account
            }

            generate_azure_blob_storage_overview(
                base_dir,
                project,
                dest_folder,
                azure_config,
                target_containers=target_containers,
                max_blobs_per_container=max_blobs_per_container,
                output_format="json"
            )

            logger.info(f"Scanning Azure Blob Storage completed for project: {project}")

        except Exception as e:
            logger.error(f"Scanning Azure Blob Storage failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info("No Azure Blob Storage Integration Found!")

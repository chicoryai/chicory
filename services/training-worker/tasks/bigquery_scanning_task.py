import os
import sys

from services.customer.personalization import get_project_config
from services.utils.logger import logger
from services.training.utils.bigquery_metadata_generator import generate_bigquery_overview


def run(config):
    logger.info("Analyzing for BigQuery...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Fetch BigQuery connection details from environment
    bigquery_project_id = os.getenv(f"{project.upper()}_BIGQUERY_PROJECT_ID",
                                    os.getenv("BIGQUERY_PROJECT_ID", None))
    bigquery_private_key_id = os.getenv(f"{project.upper()}_BIGQUERY_PRIVATE_KEY_ID",
                                        os.getenv("BIGQUERY_PRIVATE_KEY_ID", None))
    bigquery_private_key = os.getenv(f"{project.upper()}_BIGQUERY_PRIVATE_KEY",
                                     os.getenv("BIGQUERY_PRIVATE_KEY", None))
    bigquery_client_email = os.getenv(f"{project.upper()}_BIGQUERY_CLIENT_EMAIL",
                                      os.getenv("BIGQUERY_CLIENT_EMAIL", None))
    bigquery_client_id = os.getenv(f"{project.upper()}_BIGQUERY_CLIENT_ID",
                                   os.getenv("BIGQUERY_CLIENT_ID", None))
    bigquery_client_cert_url = os.getenv(f"{project.upper()}_BIGQUERY_CLIENT_CERT_URL",
                                         os.getenv("BIGQUERY_CLIENT_CERT_URL", None))
    bigquery_dataset_id = os.getenv(f"{project.upper()}_BIGQUERY_DATASET_ID",
                                    os.getenv("BIGQUERY_DATASET_ID", None))
    bigquery_location = os.getenv(f"{project.upper()}_BIGQUERY_LOCATION",
                                  os.getenv("BIGQUERY_LOCATION", "US"))

    # Check if we have the required credentials
    required_creds = [bigquery_project_id, bigquery_private_key_id, bigquery_private_key,
                      bigquery_client_email, bigquery_client_id]

    if all(required_creds):
        # tabular data
        dest_folder = f'{base_dir}/{project}/raw/data'
        logger.info(f"Using BigQuery project: {bigquery_project_id}, location: {bigquery_location}")

        try:
            if bigquery_project_id:
                logger.info("Generating BigQuery overview...")

                # Parse target datasets from environment variable
                target_datasets = None
                if bigquery_dataset_id:
                    # Parse comma-separated list from environment variable
                    target_datasets = [ds.strip() for ds in bigquery_dataset_id.split(',')]
                    logger.info(f"Target datasets from environment: {target_datasets}")

                # Create service account credentials dictionary for the generator
                service_account_info = {
                    "type": "service_account",
                    "project_id": bigquery_project_id,
                    "private_key_id": bigquery_private_key_id,
                    "private_key": bigquery_private_key.replace('\\n', '\n'),  # Handle escaped newlines
                    "client_email": bigquery_client_email,
                    "client_id": bigquery_client_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }

                if bigquery_client_cert_url:
                    service_account_info["client_x509_cert_url"] = bigquery_client_cert_url

                generate_bigquery_overview(
                    base_dir,
                    project,
                    dest_folder,
                    target_datasets=target_datasets,
                    service_account_info=service_account_info,
                    output_format="both"
                )
            else:
                logger.info(f"No project/datasets passed for project: {project}")
            logger.info(f"Scanning BigQuery completed for project: {project}")
        except Exception as e:
            logger.error(f"Scanning BigQuery failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info(f"No BigQuery Integration Found!")

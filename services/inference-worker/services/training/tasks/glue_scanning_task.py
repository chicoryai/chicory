import os
import sys

from services.customer.personalization import get_project_config
from services.utils.logger import logger
from services.training.utils.glue_metadata_generator import generate_glue_overview


def run(config):
    logger.info("Analyzing for AWS Glue...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Fetch AWS Glue connection details from environment
    # Using AWS IAM role-based authentication with customer account
    glue_customer_account_id = os.getenv(f"{project.upper()}_GLUE_CUSTOMER_ACCOUNT_ID",
                                         os.getenv("GLUE_CUSTOMER_ACCOUNT_ID", None))
    glue_role_name = os.getenv(f"{project.upper()}_GLUE_ROLE_NAME",
                                os.getenv("GLUE_ROLE_NAME", None))
    glue_external_id = os.getenv(f"{project.upper()}_GLUE_EXTERNAL_ID",
                                  os.getenv("GLUE_EXTERNAL_ID", None))
    glue_region = os.getenv(f"{project.upper()}_GLUE_REGION",
                            os.getenv("GLUE_REGION", "us-east-1"))
    glue_database_names = os.getenv(f"{project.upper()}_GLUE_DATABASE_NAMES",
                                    os.getenv("GLUE_DATABASE_NAMES", None))

    # Check if we have the required credentials
    required_creds = [glue_customer_account_id, glue_role_name, glue_external_id]

    if all(required_creds):
        # tabular data
        dest_folder = f'{base_dir}/{project}/raw/data'
        logger.info(f"Using AWS Glue account: {glue_customer_account_id}, region: {glue_region}")

        try:
            if glue_customer_account_id:
                logger.info("Generating AWS Glue overview...")

                # Parse target databases from environment variable
                target_databases = None
                if glue_database_names:
                    # Parse comma-separated list from environment variable
                    target_databases = [db.strip() for db in glue_database_names.split(',')]
                    logger.info(f"Target databases from environment: {target_databases}")

                # Create AWS IAM role configuration for the generator
                iam_role_config = {
                    "customer_account_id": glue_customer_account_id,
                    "role_name": glue_role_name,
                    "external_id": glue_external_id,
                    "region": glue_region
                }

                generate_glue_overview(
                    base_dir,
                    project,
                    dest_folder,
                    target_databases=target_databases,
                    iam_role_config=iam_role_config,
                    output_format="both"
                )
            else:
                logger.info(f"No customer account ID passed for project: {project}")
            logger.info(f"Scanning AWS Glue completed for project: {project}")
        except Exception as e:
            logger.error(f"Scanning AWS Glue failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info(f"No AWS Glue Integration Found!")

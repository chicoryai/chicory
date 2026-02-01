import os
import sys

from services.customer.personalization import get_project_config
from services.utils.logger import logger
from services.training.utils.redshift_metadata_generator import generate_redshift_overview


def run(config):
    logger.info("Analyzing for Redshift...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Fetch Redshift connection details from environment
    redshift_host = os.getenv(f"{project.upper()}_REDSHIFT_HOST",
                              os.getenv("REDSHIFT_HOST", None))
    redshift_port = os.getenv(f"{project.upper()}_REDSHIFT_PORT",
                              os.getenv("REDSHIFT_PORT", "5439"))
    redshift_database = os.getenv(f"{project.upper()}_REDSHIFT_DATABASE",
                                  os.getenv("REDSHIFT_DATABASE", None))
    redshift_user = os.getenv(f"{project.upper()}_REDSHIFT_USER",
                              os.getenv("REDSHIFT_USER", None))
    redshift_password = os.getenv(f"{project.upper()}_REDSHIFT_PASSWORD",
                                  os.getenv("REDSHIFT_PASSWORD", None))

    # Check if we have the required credentials
    required_creds = [redshift_host, redshift_database, redshift_user, redshift_password]

    if all(required_creds):
        # tabular data
        dest_folder = f'{base_dir}/{project}/raw/data'
        logger.info(f"Using Redshift cluster: {redshift_host}:{redshift_port}, database: {redshift_database}")

        try:
            logger.info("Generating Redshift overview...")

            # Create connection info dictionary for the generator
            connection_info = {
                "host": redshift_host,
                "port": int(redshift_port),
                "database": redshift_database,
                "user": redshift_user,
                "password": redshift_password
            }

            generate_redshift_overview(
                base_dir,
                project,
                dest_folder,
                connection_info=connection_info,
                output_format="both"
            )
            
            logger.info(f"Scanning Redshift completed for project: {project}")
        except Exception as e:
            logger.error(f"Scanning Redshift failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info(f"No Redshift Integration Found!")

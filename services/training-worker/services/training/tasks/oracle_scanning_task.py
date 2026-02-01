import os

from services.customer.personalization import get_project_config
from services.training.utils.oracle_metadata_generator import generate_oracle_overview
from services.utils.logger import logger


def run(config):
    logger.info("Analysing...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    oracle_username = os.getenv(f"{project.upper()}_ORACLE_USERNAME", os.getenv("ORACLE_USERNAME", None))
    oracle_password = os.getenv(f"{project.upper()}_ORACLE_PASSWORD", os.getenv("ORACLE_PASSWORD", None))
    oracle_dsn = os.getenv(f"{project.upper()}_ORACLE_DSN", os.getenv("ORACLE_DSN", None))
    oracle_owner = os.getenv(f"{project.upper()}_ORACLE_OWNER", os.getenv("ORACLE_OWNER", None))

    if all([oracle_username, oracle_password, oracle_dsn]):
        try:
            dest_folder = os.path.join(base_dir, project, "raw", "data")
            # Parse target schemas from environment variable
            target_schemas = None
            if oracle_owner:
                target_schemas = [owner.strip() for owner in oracle_owner.split(',')]
                logger.info(f"Target schemas from environment: {target_schemas}")

            generate_oracle_overview(
                base_dir,
                project,
                dest_folder,
                None,  # oracle_schemas configuration
                target_schemas=target_schemas,
                output_format="json"
            )
            logger.info(f"Scanning oracle completed for project: {project}")
        except Exception as e:
            logger.error(f"Scanning oracle failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info(f"No Oracle Catalog/Schema Integration Found!")

import os

from services.customer.personalization import get_project_config
from services.utils.logger import logger
from services.training.utils.snowflake_metadata_generator import generate_snowflake_overview


def run(config):
    logger.info("Analyzing for Snowflake...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Fetch required Snowflake connection details from environment
    snowflake_user = os.getenv(f"{project.upper()}_SNOWFLAKE_USERNAME", os.getenv("SNOWFLAKE_USERNAME", None))
    snowflake_account = os.getenv(f"{project.upper()}_SNOWFLAKE_ACCOUNT", os.getenv("SNOWFLAKE_ACCOUNT", None))
    snowflake_warehouse = os.getenv(f"{project.upper()}_SNOWFLAKE_WAREHOUSE", os.getenv("SNOWFLAKE_WAREHOUSE", None))

    # Fetch authentication credentials (password OR private_key required)
    snowflake_password = os.getenv(f"{project.upper()}_SNOWFLAKE_PASSWORD", os.getenv("SNOWFLAKE_PASSWORD", None))
    snowflake_private_key = os.getenv(f"{project.upper()}_SNOWFLAKE_PRIVATE_KEY", os.getenv("SNOWFLAKE_PRIVATE_KEY", None))
    snowflake_private_key_passphrase = os.getenv(f"{project.upper()}_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE",
                                                   os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", None))

    # Fetch optional connection parameters
    snowflake_database = os.getenv(f"{project.upper()}_SNOWFLAKE_DATABASE", os.getenv("SNOWFLAKE_DATABASE", None))
    snowflake_schema = os.getenv(f"{project.upper()}_SNOWFLAKE_SCHEMA", os.getenv("SNOWFLAKE_SCHEMA", None))
    snowflake_role = os.getenv(f"{project.upper()}_SNOWFLAKE_ROLE", os.getenv("SNOWFLAKE_ROLE", None))

    # Validate required fields and authentication method
    if not snowflake_user or not snowflake_account:
        logger.info("Missing required Snowflake configuration: user and account are required")
        return None

    if not snowflake_password and not snowflake_private_key:
        logger.info("Missing Snowflake authentication: either password or private_key is required")
        return None

    if snowflake_user and snowflake_account and (snowflake_password or snowflake_private_key):
        # tabular data
        dest_folder = f'{base_dir}/{project}/raw/data'
        logger.info(f"Using Snowflake account: {snowflake_account}, user: {snowflake_user}")

        try:
            logger.info("Generating Snowflake overview...")

            # Parse target databases from environment variable
            target_databases = None
            if snowflake_database:
                # Parse comma-separated list from environment variable
                target_databases = [db.strip() for db in snowflake_database.split(',')]
                logger.info(f"Target databases from environment: {target_databases}")

            # Parse target schemas from environment variable
            target_schemas = None
            if snowflake_schema:
                # Parse comma-separated list from environment variable
                target_schemas = [schema.strip() for schema in snowflake_schema.split(',')]
                logger.info(f"Target schemas from environment: {target_schemas}")

            # Replace literal \n with actual newlines
            snowflake_private_key = snowflake_private_key.replace('\\\\n', '\n').replace('\\n', '\n') if snowflake_private_key else None
            snowflake_private_key_passphrase = snowflake_private_key_passphrase.replace('\\\\n', '\n').replace('\\n', '\n') if snowflake_private_key_passphrase else None

            # Build Snowflake connection config from environment variables
            snowflake_config = {
                "account": snowflake_account,
                "user": snowflake_user,
                "password": snowflake_password,
                "private_key": snowflake_private_key,
                "private_key_passphrase": snowflake_private_key_passphrase,
                "warehouse": snowflake_warehouse,
                "database": snowflake_database,
                "schema": snowflake_schema,
                "role": snowflake_role,
            }

            # Remove None values from config
            snowflake_config = {k: v for k, v in snowflake_config.items() if v is not None}

            # Log authentication method
            auth_method = "private key" if snowflake_private_key else "password"
            logger.info(f"Using Snowflake account: {snowflake_config['account']}, user: {snowflake_config['user']}, auth: {auth_method}")

            generate_snowflake_overview(
                base_dir,
                project,
                dest_folder,
                snowflake_config,
                target_databases=target_databases,
                target_schemas=target_schemas,
                output_format="json"
            )
            logger.info(f"Scanning Snowflake completed for project: {project}")
        except Exception as e:
            logger.error(f"Scanning Snowflake failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info(f"No Snowflake Integration Found!")

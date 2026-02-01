import os

from services.customer.personalization import get_project_config
from services.integration.confluence import download_space
from services.utils.logger import logger


def run(config):
    logger.info("Analysing...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    # Configuration
    base_url = os.getenv(f"{project.upper()}_CONFLUENCE_BASE_URL", os.getenv("CONFLUENCE_BASE_URL", None))
    api_token = os.getenv(f"{project.upper()}_CONFLUENCE_API_TOKEN", os.getenv("CONFLUENCE_API_TOKEN", None))
    space_key = os.getenv(f"{project.upper()}_CONFLUENCE_SPACE_KEY", os.getenv("CONFLUENCE_SPACE_KEY", None))
    email = os.getenv(f"{project.upper()}_CONFLUENCE_EMAIL", os.getenv("CONFLUENCE_EMAIL", None))

    if base_url and api_token and space_key:
        try:
            save_path = os.path.join(base_dir, project, "raw", "documents", "confluence")
            os.makedirs(save_path, exist_ok=True) # making sure path exists
            download_space(space_key, api_token, email, base_url, save_path)
            logger.info(f"Scanning confluence completed with project: {project}")
        except Exception as e:
            logger.error(f"Scanning confluence space failed for: {project}")
            logger.error(f"An error occurred: {str(e)}", exc_info=True)
    else:
        logger.info(f"No Confluence Space Integration Found!")

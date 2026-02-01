import os

from services.customer.personalization import get_project_config
from services.integration.github import get_repositories, clone_repo
from services.utils.logger import logger


def run(config):
    logger.info("Analysing...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    project_config = get_project_config(project)
    if not project_config:
        logger.error("Project NOT supported yet!")
        return None

    github_username = os.getenv(f"{project.upper()}_GITHUB_USERNAME", os.getenv("GITHUB_USERNAME", None))
    github_access_token = os.getenv(f"{project.upper()}_GITHUB_ACCESS_TOKEN", os.getenv("GITHUB_ACCESS_TOKEN", None))
    github_base_url = os.getenv(f"{project.upper()}_GITHUB_BASE_URL", os.getenv("GITHUB_BASE_URL", None))

    if github_username and github_access_token and github_base_url:
        clone_dir = f'{base_dir}/{project}/raw/code/github'
        if not os.path.exists(clone_dir):
            os.makedirs(clone_dir)
        try:
            repos = get_repositories(github_access_token, github_base_url)
            if repos:
                logger.debug(f"Repositories found: {repos}")
            for repo in repos:
                repo_name = repo["name"]
                repo_url = repo["clone_url"]
                clone_repo(repo_url, repo_name, clone_dir, github_username, github_access_token)
            logger.info("All Github repositories have been cloned!")
        except Exception as e:
            logger.error(f"Scanning github failed for: {project}")
            logger.error(e, exc_info=True)
    else:
        logger.info(f"No Github Project Integration Found!")

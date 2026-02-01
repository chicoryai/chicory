import os

from services.training.tasks import github_scanning_task
from services.utils.logger import logger


def run(config):
    logger.info("Analysing...")

    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    if config["DISABLE_GITHUB_SCANNING"].lower() == "false":
        # Github scanning task
        logger.info("Running Github scanning task...")
        github_scanning_task.run(config)
    else:
        logger.info("Github scanning skipped...")

import os

from services.training.tasks import confluence_space_scanning_task, google_doc_scanning_task, web_scrapping_task, webfetch_scanning_task
from services.utils.logger import logger


async def run(config, data_sources=None):
    logger.info("Analysing...")

    if config["DISABLE_WEB_SCRAPING"].lower() == "false":
        # Web scraping task
        logger.info("Running web scraping task...")
        await web_scrapping_task.run(config)
    else:
        logger.info("Web scraping skipped...")

    if config["DISABLE_GOOGLE_DOCS_SCANNING"].lower() == "false":
        # Google Docs scraping task
        logger.info("Running google docs scraping task...")
        google_doc_scanning_task.run(config)
    else:
        logger.info("Google docs scanning skipped...")

    if config["DISABLE_CONFLUENCE_SCANNING"].lower() == "false":
        # Confluence scraping task
        logger.info("Running confluence scraping task...")
        confluence_space_scanning_task.run(config)
    else:
        logger.info("Confluence scanning skipped...")

    if config.get("DISABLE_WEBFETCH_SCANNING", "false").lower() == "false":
        # Webfetch scanning task (Firecrawl)
        logger.info("Running webfetch scanning task...")
        await webfetch_scanning_task.run(config, data_sources)
    else:
        logger.info("Webfetch scanning skipped...")

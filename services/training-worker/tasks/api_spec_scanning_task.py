import os

from services.utils.logger import logger
from services.utils.tools import fix_ref_paths


def run(config):
    logger.info("Analysing...")

    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    raw_path = os.path.join(base_dir, project, "raw", "api")

    # if raw data has been uploaded directly to s3
    try:
        fix_ref_paths(raw_path)
    except Exception as e:
        logger.error(f"Error: {e}")

    # TODO: download urls directly from net support

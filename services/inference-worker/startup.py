import os
import shutil
import sys
import time

from services.integration.s3_sync import sync_s3_from_bucket
from services.utils.config import load_default_envs
from services.utils.logger import logger

if __name__ == "__main__":
    logger.info("Loading Inference Service ...")
    load_default_envs()
    home_path = os.getenv("HOME_PATH")
    data_path = os.getenv("BASE_DIR")
    force_sync = os.getenv("FORCE_SYNC", "False").lower() == "true"

    # Ensure essential environment variables are set
    required_env_vars = ["PROJECT", "S3_BUCKET", "S3_REGION", "OPENAI_API_KEY"]
    for var in required_env_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"Missing required environment variable: {var}")

    project_name = os.getenv("PROJECT").lower()
    project_path = os.path.join(data_path, project_name)

    # Ensure the data directory exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        logger.info(f"Created data directory at {data_path}")

    # Remove existing project path if force_sync is enabled
    if force_sync and os.path.exists(project_path):
        start_time = time.time()
        try:
            if os.path.isdir(project_path):
                shutil.rmtree(project_path)  # Remove directory and contents
            elif os.path.isfile(project_path):
                os.remove(project_path)  # Remove single file
            logger.info(f"Removed existing project path: {project_path} in {time.time() - start_time:.2f}s")
        except:
            logger.error(f"Failed to remove existing project path: {data_path} in {time.time() - start_time:.2f}s")

    wd_path = os.path.join(project_path, "wd")
    os.makedirs(wd_path, exist_ok=True)

    time.sleep(30)
    # Check if S3 sync should be skipped
    skip_s3_sync = os.getenv("SKIP_S3_SYNC", "False").lower() == "true"
    
    # Sync data from S3 if required and not explicitly skipped
    if not skip_s3_sync and (force_sync or not os.listdir(data_path)):
        logger.info("S3 sync is enabled. Proceeding with data synchronization...")
        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            logger.info("Syncing data from S3...")
            sync_s3_from_bucket(data_path)
            if os.listdir(data_path):  # Check if directory is no longer empty
                logger.info("Data sync from S3 completed.")
                break
            retry_count += 1
            logger.warning(f"Retrying data sync from S3... Attempt {retry_count}/{max_retries}")
            time.sleep(30)
        else:
            # If all retries fail, raise an exception
            error_message = "Failed to sync data from S3 after multiple attempts."
            logger.error(error_message)
            sys.exit(1)
    elif skip_s3_sync:
        logger.info("S3 sync is disabled via SKIP_S3_SYNC environment variable. Skipping data synchronization.")

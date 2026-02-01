import asyncio
import os
import time
import shutil
from datetime import datetime

from services.training.config import load_config
from services.integration.s3_sync import (
    sync_s3_from_bucket, 
    sync_to_s3_with_delete, 
    delete_s3_path_contents
)
from services.utils.logger import logger
from services.training.tasks import (
    document_scanning_task, 
    code_scanning_task,
    data_scanning_task,
    preprocessing_task
)


def log_timing(operation_name, start_time):
    """Helper function to log operation timing"""
    duration = time.time() - start_time
    logger.info(f"Operation timing - {operation_name}: {duration:.2f} seconds")


async def setup_environment():
    """Set up the environment for training"""
    # Load configuration
    config = load_config()
    
    # Check if we're in dev mode
    dev_mode = os.getenv("DEV", "False").lower() == "true"
    skip_s3_sync = os.getenv("SKIP_S3_SYNC", "False").lower() == "true"
    # Get RESET_DATA as a string and keep it as a string for later comparison
    reset_data_str = os.getenv("RESET_DATA", "False").lower()
    
    # Setup data directories if not in dev mode
    if not dev_mode:
        data_path = os.getenv("BASE_DIR", "/data")
        project_path = os.path.join(data_path, os.getenv("PROJECT", "default").lower())
        
        # Clean up directory if it exists
        if os.path.isdir(project_path):
            start_time = time.time()
            if not skip_s3_sync or reset_data_str == "true":
                shutil.rmtree(project_path)  # Removes the directory and all its contents
            else:
                raw_folder = os.path.join(project_path, 'raw')
                # Get all items in the project directory
                for item in os.listdir(project_path):
                    item_path = os.path.join(project_path, item)
                    # Skip the raw folder
                    if item_path == raw_folder:
                        continue
                    # Remove other directories and files
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            log_timing("Project directory cleanup", start_time)
        
        # Sync from S3 if needed
        if not skip_s3_sync:
            if reset_data_str == "false":
                start_time = time.time()
                logger.info("Syncing (existing) data from S3...")
                sync_s3_from_bucket(data_path)
                log_timing("S3 sync from bucket", start_time)
            else:
                bucket = os.getenv("S3_BUCKET")
                region = os.getenv("S3_REGION")
                project = os.getenv("PROJECT", "default").lower()
                start_time = time.time()
                logger.info(f"Deleting S3 path contents for project {project} with RESET_DATA={reset_data_str}...")
                delete_s3_path_contents(bucket, project, region)
                sync_s3_from_bucket(data_path)
                log_timing("S3 path deletion except `raw`", start_time)
    
    return config, dev_mode, skip_s3_sync


async def run_data_scanning(config):
    """Run the data scanning task"""
    if os.getenv("SKIP_PREPARE", "False").lower() != "true":
        task_start = time.time()
        logger.info("Running Data scanning task...")
        data_scanning_task.run(config)
        log_timing("Data scanning task", task_start)
        return True
    return False


async def run_code_scanning(config):
    """Run the code scanning task"""
    if os.getenv("SKIP_PREPARE", "False").lower() != "true":
        task_start = time.time()
        logger.info("Running Code scanning task...")
        code_scanning_task.run(config)
        log_timing("Code scanning task", task_start)
        return True
    return False


async def run_document_scanning(config):
    """Run the document scanning task"""
    if os.getenv("SKIP_PREPARE", "False").lower() != "true":
        task_start = time.time()
        logger.info("Running Documents scanning task...")
        await document_scanning_task.run(config)
        log_timing("Documents scanning task", task_start)
        return True
    return False


async def run_preprocessing(config):
    """Run the preprocessing task with proper error handling"""
    if os.getenv("SKIP_PREPARE", "False").lower() != "true":
        task_start = time.time()
        logger.info("Running preprocessing task...")

        try:
            # Call preprocessing with progress callback and proper error handling
            preprocessing_task.run(config)
            logger.info(f"Preprocessing completed")
            log_timing("Preprocessing task", task_start)
            return True
        except Exception as e:
            log_timing("Preprocessing task (FAILED)", task_start)
            logger.error(f"Preprocessing task failed: {str(e)}", exc_info=True)
    else:
        logger.info("Skipping preprocessing task (SKIP_PREPARE=true)")
        return {"status": "skipped", "reason": "skip_prepare_enabled"}


async def run_s3_sync(dev_mode, skip_s3_sync):
    """Sync data back to S3 after completion"""
    if not dev_mode and not skip_s3_sync:
        data_path = os.getenv("BASE_DIR", "/data")
        start_time = time.time()
        logger.info("Syncing data back to S3...")
        sync_to_s3_with_delete(data_path)
        log_timing("S3 sync to bucket", start_time)
        return True
    elif skip_s3_sync:
        logger.info("Skipping S3 sync as SKIP_S3_SYNC is enabled")
    return False


async def run_training_workflow():
    """Run the entire training workflow"""
    total_start_time = time.time()
    
    try:
        logger.info(f"Starting training workflow at {datetime.now().isoformat()}")
        
        # Setup environment
        config, dev_mode, skip_s3_sync = await setup_environment()
        
        # Run all tasks in sequence
        await run_data_scanning(config)
        await run_code_scanning(config)
        await run_document_scanning(config)
        await run_preprocessing(config)
        await run_s3_sync(dev_mode, skip_s3_sync)
        
        total_duration = time.time() - total_start_time
        logger.info(f"Training workflow completed successfully. Total duration: {total_duration:.2f} seconds")
        return True
    
    except Exception as e:
        total_duration = time.time() - total_start_time
        logger.error(f"Error occurred during training workflow execution after {total_duration:.2f} seconds: {e}", exc_info=True)
        raise

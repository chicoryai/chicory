import asyncio
import os
import time
from datetime import datetime

# Import Phoenix for tracing
from services.integration.phoenix import initialize_phoenix

# Import config utilities
from services.utils.config import load_default_envs
from services.utils.logger import logger

# Load default ENVs
load_default_envs()

# Import our modular training steps
from services.training.training_steps import (
    run_training_workflow
)

# Environment flags
dev_mode = os.getenv("DEV", "False").lower() == "true"
skip_prep = os.getenv("SKIP_PREPARE", "False").lower() == "true"

async def run_cronjob():
    """
    Main function for running the cronjob tasks in sequence.
    This now uses the modular training steps from training_steps.py
    """
    # We're now delegating to our modular implementation
    return await run_training_workflow()


if __name__ == "__main__":
    from dotenv import load_dotenv

    # Load environment variables from .env file
    dotenv_path = os.getenv("DOTENV_PATH", ".env")
    load_dotenv(dotenv_path)

    # Initialize Phoenix Tracing
    if "PHOENIX_PROJECT_NAME" not in os.environ:
        os.environ["PHOENIX_PROJECT_NAME"] = "chicory-training"
    initialize_phoenix()

    # Ensure essential environment variables are set
    required_env_vars = ["PROJECT", "S3_BUCKET", "S3_REGION", "OPENAI_API_KEY"]
    for var in required_env_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"Missing required environment variable: {var}")

    # Ensure PROJECT is lowercase for consistent directory naming
    if os.getenv("PROJECT"):
        os.environ["PROJECT"] = os.getenv("PROJECT").lower()
        logger.debug(f"Normalized PROJECT environment variable to lowercase: {os.environ['PROJECT']}")

    if not os.getenv("USER_AGENT"):
        os.environ['USER_AGENT'] = "chicory_" + os.getenv("PROJECT")

    home_path = os.getenv("HOME_PATH", "/app")
    data_path = os.getenv("BASE_DIR", os.path.join(home_path, "data"))

    # Ensure the data directory exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        logger.info(f"Created data directory at {data_path}")

    run_training = os.getenv("RUN_TRAINING", "True")

    if run_training.strip().lower() == "true":
        # Run the cronjob - all the setup is now handled in training_steps.py
        asyncio.run(run_cronjob())
    else:
        logger.info("CronJob skipped.")

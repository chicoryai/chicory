import os
from typing import Dict, Any

from services.utils.logger import logger
from services.utils.preprocessing.preprocessor import ProcessingConfig, Preprocess


def run(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run preprocessing task with proper error handling and configuration respect

    Args:
        config: Training configuration dictionary

    Returns:
        Dictionary with processing results

    Raises:
        Exception: If preprocessing fails
    """
    logger.info("Starting preprocessing task...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    # Create processing directory path
    processing_dir = os.path.join(base_dir, project, "raw")

    if not os.path.exists(processing_dir):
        logger.warning(f"Processing directory does not exist: {processing_dir}")
        return {
            "status": "skipped",
            "reason": "no_raw_directory",
            "files_processed": 0,
            "files_split": 0
        }

    try:
        # Respect training configuration with safe defaults
        processing_config = ProcessingConfig(
            max_file_size_mb=1.0,
            delete_original=True,
            chunk_overlap=100,
            max_total_size_gb=5.0,  # 5GB processing limit
            max_files_per_run=500,  # 500 files limit
        )

        logger.info(f"Preprocessing configuration: max_file_size={processing_config.max_file_size_mb}MB, "
                   f"delete_original={processing_config.delete_original}")

        preprocessor = Preprocess(processing_config)

        result = preprocessor.process(processing_dir, recursive=True)

        # Extract statistics for return
        stats = preprocessor.stats
        files_processed = stats.get('files_processed', 0)
        files_split = stats.get('files_split', 0)
        chunks_created = stats.get('chunks_created', 0)

        logger.info(
            f"Preprocessing completed successfully: {files_processed} files processed, "
            f"{files_split} files split into {chunks_created} chunks"
        )

        return {
            "status": "success",
            "files_processed": files_processed,
            "files_split": files_split,
            "chunks_created": chunks_created,
            "processing_summary": result
        }

    except Exception as e:
        error_msg = f"Preprocessing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Re-raise with more specific error type to preserve error context
        if isinstance(e, (OSError, IOError, PermissionError)):
            raise type(e)(error_msg) from e
        elif isinstance(e, (ValueError, TypeError)):
            raise type(e)(error_msg) from e
        elif isinstance(e, RuntimeError):
            raise RuntimeError(error_msg) from e
        else:
            # For unknown exceptions, use generic RuntimeError but preserve original
            raise RuntimeError(error_msg) from e

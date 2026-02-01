import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import urllib3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

from services.utils.logger import logger

logging.getLogger('boto3').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.INFO)

#Configure log level
for name in logging.Logger.manager.loggerDict.keys():
    if name in ('boto', 'urllib3', 's3transfer', 'boto3', 'botocore', 'nose'):
        logging.getLogger(name).setLevel(logger.level)

# Configure connection pool and boto3 config
MAX_POOL_CONNECTIONS = 50
urllib3.PoolManager(maxsize=MAX_POOL_CONNECTIONS)
boto_config = Config(
    max_pool_connections=MAX_POOL_CONNECTIONS,
    retries={'max_attempts': 3}
)

# Configure transfer settings for parallel operations
TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,  # 8MB
    max_concurrency=10,
    multipart_chunksize=8 * 1024 * 1024,  # 8MB
    use_threads=True
)

def download_file(s3, bucket, key, dest_path):
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        s3.download_file(bucket, key, dest_path, Config=TRANSFER_CONFIG)
        return key, None
    except Exception as e:
        return key, str(e)


def upload_file(s3, bucket, local_path, s3_key, base_path):
    try:
        s3_key = os.path.relpath(local_path, base_path)
        s3.upload_file(local_path, bucket, s3_key, Config=TRANSFER_CONFIG)
        return s3_key, None
    except Exception as e:
        return s3_key, str(e)


def _get_s3_client():
    """Create S3 client with optional custom endpoint (MinIO, LocalStack, etc.)"""
    region = os.getenv("S3_REGION", "us-east-1")
    endpoint_url = os.getenv("S3_ENDPOINT_URL")

    client_kwargs = {
        'region_name': region,
        'config': boto_config
    }

    # Add endpoint URL if specified (for MinIO or other S3-compatible storage)
    if endpoint_url:
        client_kwargs['endpoint_url'] = endpoint_url
        logger.info(f"Using custom S3 endpoint: {endpoint_url}")

    return boto3.client("s3", **client_kwargs)


def sync_s3_from_bucket(data_path):
    try:
        bucket = os.getenv("S3_BUCKET")
        region = os.getenv("S3_REGION", "us-east-1")

        if not bucket:
            raise ValueError("S3_BUCKET environment variable is not set")

        # Ensure data_path directory exists
        os.makedirs(data_path, exist_ok=True)

        logger.debug(f"Current folder content: {os.listdir(data_path)}")
        logger.info("Syncing from S3 bucket...")

        # Initialize S3 client with proper connection pool size (supports MinIO)
        s3 = _get_s3_client()

        # Collect all objects to download
        objects_to_download = []
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            if "Contents" in page:
                objects_to_download.extend(page["Contents"])

        if not objects_to_download:
            logger.info("No files to download from S3.")
            return

        # Download files in parallel
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for obj in objects_to_download:
                key = obj["Key"]
                dest_path = os.path.join(data_path, key)
                futures.append(
                    executor.submit(download_file, s3, bucket, key, dest_path)
                )

            # Process results and handle any errors
            for future in as_completed(futures):
                key, error = future.result()
                if error:
                    logger.error(f"Error downloading {key}: {error}")
                else:
                    logger.debug(f"Successfully downloaded: {key}")

        logger.info("[S3 DOWNLOAD] Sync from S3 completed.")
    except NoCredentialsError:
        logger.error("[S3 DOWNLOAD] AWS credentials not found. Please configure your credentials.")
        sys.exit(1)
    except PartialCredentialsError as pce:
        logger.error(f"[S3 DOWNLOAD] Incomplete AWS credentials: {pce}")
        sys.exit(1)
    except ClientError as ce:
        logger.error(f"[S3 DOWNLOAD] Error accessing S3 bucket: {ce}")
        sys.exit(1)
    except ValueError as ve:
        logger.error(f"[S3 DOWNLOAD] Configuration error: {ve}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)


def sync_s3_to_bucket(data_path):
    try:
        bucket = os.getenv("S3_BUCKET")
        region = os.getenv("S3_REGION", "us-east-1")

        if not bucket:
            raise ValueError("S3_BUCKET environment variable is not set")

        # Ensure data_path directory exists
        os.makedirs(data_path, exist_ok=True)

        logger.debug(f"Current folder content: {os.listdir(data_path)}")
        logger.info("Syncing local data to S3 bucket...")

        # Initialize S3 client with proper connection pool size (supports MinIO)
        s3 = _get_s3_client()

        # Collect all files to upload
        files_to_upload = []
        for root, _, files in os.walk(data_path):
            for file in files:
                local_path = os.path.join(root, file)
                files_to_upload.append(local_path)

        if not files_to_upload:
            logger.info("No files to upload to S3.")
            return

        # Upload files in parallel
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for local_path in files_to_upload:
                s3_key = os.path.relpath(local_path, data_path)
                futures.append(
                    executor.submit(upload_file, s3, bucket, local_path, s3_key, data_path)
                )

            # Process results and handle any errors
            for future in as_completed(futures):
                key, error = future.result()
                if error:
                    logger.error(f"Error uploading {key}: {error}")
                else:
                    logger.debug(f"Successfully uploaded: {key}")

        logger.info("[S3 UPLOAD] Sync to S3 completed.")
    except NoCredentialsError:
        logger.error("[S3 UPLOAD] AWS credentials not found. Please configure your credentials.")
        sys.exit(1)
    except PartialCredentialsError as pce:
        logger.error(f"[S3 UPLOAD] Incomplete AWS credentials: {pce}")
        sys.exit(1)
    except ClientError as ce:
        logger.error(f"[S3 UPLOAD] Error accessing S3 bucket: {ce}")
        sys.exit(1)
    except ValueError as ve:
        logger.error(f"[S3 UPLOAD] Configuration error: {ve}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"[S3 UPLOAD] An unexpected error occurred: {e}")
        sys.exit(1)


def sync_to_s3_with_delete(data_path):
    """Sync local files to S3 and delete extra files from the bucket."""
    try:
        bucket = os.getenv("S3_BUCKET")

        # Initialize S3 client (supports MinIO)
        s3 = _get_s3_client()

        # Get a list of all objects currently in the S3 bucket
        existing_objects = []
        try:
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket):
                if "Contents" in page:
                    existing_objects.extend([obj["Key"] for obj in page["Contents"]])
        except ClientError as ce:
            print(f"Error while listing objects in bucket {bucket}: {ce}")
            raise

        # Walk through the local directory and upload files to S3
        local_files = []
        for root, _, files in os.walk(data_path):
            for file in files:
                local_path = os.path.join(root, file)
                s3_key = os.path.relpath(local_path, data_path)
                local_files.append(s3_key)  # Keep track of all local files
                try:
                    s3.upload_file(local_path, bucket, s3_key, Config=TRANSFER_CONFIG)
                except ClientError as ce:
                    print(f"Error while uploading {local_path} to bucket {bucket}: {ce}")
                    raise

        # Identify and delete files that exist in S3 but not in the local directory
        files_to_delete = set(existing_objects) - set(local_files)
        for s3_key in files_to_delete:
            try:
                print(f"Deleting {s3_key} from S3 bucket {bucket}")
                s3.delete_object(Bucket=bucket, Key=s3_key)
            except ClientError as ce:
                print(f"Error while deleting {s3_key} from bucket {bucket}: {ce}")
                raise

        logger.info("Sync to S3 completed.")

    except NoCredentialsError:
        print("AWS credentials not found. Please configure your credentials.")
        raise
    except PartialCredentialsError as pce:
        print(f"Incomplete AWS credentials: {pce}")
        raise
    except ClientError as ce:
        print(f"Error interacting with S3: {ce}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise


def delete_s3_path_contents(bucket_name, path_prefix, region=None):
    """
    Delete all objects under a specified path in an S3 bucket, except for the 'raw' subfolder.

    :param bucket_name: Name of the S3 bucket.
    :param path_prefix: Path prefix within the bucket to target for deletion.
    :param region: AWS region where the bucket is located (optional, uses env var if not provided).
    """
    try:
        # Initialize S3 client (supports MinIO)
        s3 = _get_s3_client()

        # Ensure path_prefix ends with a slash to avoid partial matches
        if not path_prefix.endswith('/'):
            path_prefix = path_prefix + '/'

        # Create a reusable Paginator
        paginator = s3.get_paginator('list_objects_v2')

        # Create a PageIterator from the Paginator
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=path_prefix)

        # Collect all object keys to delete, excluding the 'raw' subfolder
        objects_to_delete = []
        raw_prefix = path_prefix + "raw/"

        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Skip objects in the raw folder
                    if not obj['Key'].startswith(raw_prefix):
                        objects_to_delete.append({'Key': obj['Key']})

        # Delete objects in batches
        if objects_to_delete:
            # Boto3 allows up to 1000 objects to be deleted in a single request
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i + 1000]
                response = s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': batch}
                )
                # Check for errors in the response
                if 'Errors' in response:
                    for error in response['Errors']:
                        logger.error(f"Error deleting {error['Key']}: {error['Message']}")
                else:
                    logger.info(
                        f"Deleted {len(batch)} objects from {bucket_name}/{path_prefix} (excluding 'raw' subfolder)")
        else:
            logger.info(f"No objects found at {bucket_name}/{path_prefix} to delete (excluding 'raw' subfolder).")

    except NoCredentialsError:
        logger.error("[S3 DELETE] AWS credentials not found. Please configure your credentials.")
    except PartialCredentialsError as pce:
        logger.error(f"[S3 DELETE] Incomplete AWS credentials: {pce}")
    except ClientError as ce:
        logger.error(f"[S3 DELETE] Error accessing S3 bucket: {ce}")
    except ValueError as ve:
        logger.error(f"[S3 DELETE] Configuration error: {ve}")
    except Exception as e:
        logger.error(f"[S3 DELETE] An unexpected error occurred: {e}")


def clean_s3_bucket_except(bucket_name, region, save_paths):
    """
    Clean all objects in an S3 bucket except those in specified folders or paths.

    :param bucket_name: Name of the S3 bucket to clean.
    :param region: AWS region of the bucket (optional, uses env var if not provided).
    :param save_paths: List of folder prefixes or paths to preserve. For example: ["folder1/", "folder2/subfolder/"].
    """
    try:
        # Initialize S3 client (supports MinIO)
        s3 = _get_s3_client()

        # Create a reusable Paginator
        paginator = s3.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket_name)

        # Collect objects to delete
        objects_to_delete = []
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']

                    # Check if the key matches any save paths
                    if not any(key.startswith(save_path) for save_path in save_paths):
                        objects_to_delete.append({'Key': key})

        # Perform deletion in batches
        if objects_to_delete:
            logger.info(f"Found {len(objects_to_delete)} objects to delete.")
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i + 1000]
                response = s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': batch}
                )
                if 'Errors' in response:
                    for error in response['Errors']:
                        logger.error(f"[S3 CLEAN] Error deleting {error['Key']}: {error['Message']}")
                else:
                    logger.info(f"[S3 CLEAN] Deleted {len(batch)} objects.")
        else:
            logger.info("[S3 CLEAN] No objects found to delete.")
    except NoCredentialsError:
        logger.error("[S3 CLEAN] AWS credentials not found. Please configure your credentials.")
        raise
    except PartialCredentialsError as pce:
        logger.error(f"[S3 CLEAN] Incomplete AWS credentials: {pce}")
        raise
    except ClientError as ce:
        logger.error(f"[S3 CLEAN] Error interacting with S3: {ce}")
        raise
    except Exception as e:
        logger.error(f"[S3 CLEAN] An unexpected error occurred: {e}")
        raise

def list_s3_bucket_contents(bucket_name, region=None, recursive=True, human_readable=True, summarize=True):
    """
    List contents of an S3 bucket, replicating `aws s3 ls` functionality.

    :param bucket_name: Name of the S3 bucket.
    :param region: AWS region of the bucket (optional, uses env var if not provided).
    :param recursive: Whether to list contents recursively.
    :param human_readable: Format file sizes in human-readable format.
    :param summarize: Show summary of total objects and size.
    """
    try:
        # Initialize S3 client (supports MinIO)
        s3 = _get_s3_client()

        # Create a reusable Paginator
        paginator = s3.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket_name)

        total_size = 0
        total_files = 0

        logger.info(f"Contents of bucket: {bucket_name}")

        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    size = obj['Size']
                    last_modified = obj['LastModified']

                    # Format size
                    if human_readable:
                        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                            if size < 1024.0:
                                size_str = f"{size:.2f} {unit}"
                                break
                            size /= 1024.0
                    else:
                        size_str = f"{size} bytes"

                    # Format last modified date
                    last_modified_str = last_modified.strftime('%Y-%m-%d %H:%M:%S')

                    # Print details
                    logger.info(f"{last_modified_str}  {size_str:>10}  {key}")

                    # Update summary details
                    total_size += obj['Size']
                    total_files += 1

        if summarize:
            # Summarize total objects and size
            total_size_str = f"{total_size} bytes"
            if human_readable:
                total_size_hr = total_size
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if total_size_hr < 1024.0:
                        total_size_str = f"{total_size_hr:.2f} {unit}"
                        break
                    total_size_hr /= 1024.0
            logger.info("\nSummary:")
            logger.info(f"Total Objects: {total_files}")
            logger.info(f"Total Size: {total_size_str}")

    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure your credentials.")
    except PartialCredentialsError as pce:
        logger.error(f"Incomplete AWS credentials: {pce}")
    except ClientError as ce:
        logger.error(f"Error accessing S3 bucket: {ce}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def delete_files_with_extensions(bucket_name, region, prefix, extensions):
    """
    Delete files from an S3 bucket that end with specific extensions.

    :param bucket_name: Name of the S3 bucket.
    :param region: AWS region where the bucket is located (optional, uses env var if not provided).
    :param prefix: Prefix to filter objects in the bucket (e.g., folder path).
    :param extensions: List of file extensions to delete (e.g., [".mov.txt", ".mp4.txt", ".dmg.txt"]).
    """
    try:
        # Initialize S3 client (supports MinIO)
        s3 = _get_s3_client()

        # Create a reusable Paginator
        paginator = s3.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        # Collect objects to delete
        objects_to_delete = []
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if any(key.endswith(ext) for ext in extensions):
                        objects_to_delete.append({'Key': key})

        # Delete objects in batches
        if objects_to_delete:
            logger.info(f"Found {len(objects_to_delete)} objects to delete.")
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i + 1000]
                response = s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': batch}
                )
                if 'Errors' in response:
                    for error in response['Errors']:
                        logger.error(f"Error deleting {error['Key']}: {error['Message']}")
                else:
                    logger.info(f"Deleted {len(batch)} objects.")
        else:
            logger.info("No matching objects found to delete.")

    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure your credentials.")
    except PartialCredentialsError as pce:
        logger.error(f"Incomplete AWS credentials: {pce}")
    except ClientError as ce:
        logger.error(f"Error accessing S3 bucket: {ce}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

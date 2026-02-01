"""
S3 utilities for AWS S3 operations
"""
import os
import re
import json
import boto3
import hashlib
import logging
import urllib.parse
from pathlib import Path
from datetime import datetime
from fastapi import HTTPException, status
from typing import Tuple, Dict, Any, List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Default presigned URL expiration (1 hour)
PRESIGNED_URL_EXPIRATION = 3600


def _get_s3_client_for_bucket(bucket_name: str) -> Tuple[object, str]:
    """Get an S3 client for a specific bucket.

    Args:
        bucket_name: The S3 bucket name

    Returns:
        tuple: (s3_client, s3_region)
    """
    s3_region = os.getenv("AWS_REGION", "us-east-1")
    s3_endpoint = os.getenv("S3_ENDPOINT_URL")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    client_kwargs = {'region_name': s3_region}

    # Add endpoint URL if specified (for MinIO or other S3-compatible storage)
    if s3_endpoint:
        client_kwargs['endpoint_url'] = s3_endpoint

    # Add explicit credentials if provided
    if aws_access_key and aws_secret_key:
        client_kwargs['aws_access_key_id'] = aws_access_key
        client_kwargs['aws_secret_access_key'] = aws_secret_key

    s3_client = boto3.client('s3', **client_kwargs)

    return s3_client, s3_region


async def get_s3_client() -> Tuple[object, str, str]:
    """Get an S3 client using EC2 instance IAM role or environment variables

    Supports custom S3 endpoints (MinIO, LocalStack, etc.) via S3_ENDPOINT_URL.

    Returns:
    -------
    tuple
        (s3_client, s3_bucket, s3_region) or raises HTTPException if config is missing
    """
    # Get S3 configuration from environment variables
    s3_region = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket = os.getenv("S3_BUCKET_NAME")
    s3_endpoint = os.getenv("S3_ENDPOINT_URL")

    if not s3_bucket:
        logger.error("Missing S3 bucket configuration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is not properly configured for S3 storage - missing S3_BUCKET_NAME"
        )

    # Check if explicit AWS credentials are provided
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    try:
        client_kwargs = {'region_name': s3_region}

        # Add endpoint URL if specified (for MinIO or other S3-compatible storage)
        if s3_endpoint:
            client_kwargs['endpoint_url'] = s3_endpoint
            logger.info(f"Using custom S3 endpoint: {s3_endpoint}")

        if aws_access_key and aws_secret_key:
            # Use explicit credentials if provided
            logger.info("Using explicit AWS credentials from environment variables")
            client_kwargs['aws_access_key_id'] = aws_access_key
            client_kwargs['aws_secret_access_key'] = aws_secret_key
        else:
            # Use EC2 instance IAM role credentials (default behavior)
            logger.info("Using EC2 instance IAM role credentials for S3 access")

        s3_client = boto3.client('s3', **client_kwargs)

        return s3_client, s3_bucket, s3_region
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize S3 client: {str(e)}"
        )


def get_s3_client_sync() -> Tuple[object, str, str]:
    """Synchronous version of get_s3_client for use in non-async contexts

    Supports custom S3 endpoints (MinIO, LocalStack, etc.) via S3_ENDPOINT_URL.

    Returns:
    -------
    tuple
        (s3_client, s3_bucket, s3_region) or raises Exception if config is missing
    """
    # Get S3 configuration from environment variables
    s3_region = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket = os.getenv("S3_BUCKET_NAME")
    s3_endpoint = os.getenv("S3_ENDPOINT_URL")

    if not s3_bucket:
        logger.error("Missing S3 bucket configuration")
        raise Exception("Server is not properly configured for S3 storage - missing S3_BUCKET_NAME")

    # Check if explicit AWS credentials are provided
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    try:
        client_kwargs = {'region_name': s3_region}

        # Add endpoint URL if specified (for MinIO or other S3-compatible storage)
        if s3_endpoint:
            client_kwargs['endpoint_url'] = s3_endpoint
            logger.info(f"Using custom S3 endpoint: {s3_endpoint}")

        if aws_access_key and aws_secret_key:
            # Use explicit credentials if provided
            logger.info("Using explicit AWS credentials from environment variables")
            client_kwargs['aws_access_key_id'] = aws_access_key
            client_kwargs['aws_secret_access_key'] = aws_secret_key
        else:
            # Use EC2 instance IAM role credentials (default behavior)
            logger.info("Using EC2 instance IAM role credentials for S3 access")

        s3_client = boto3.client('s3', **client_kwargs)

        return s3_client, s3_bucket, s3_region
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        raise Exception(f"Failed to initialize S3 client: {str(e)}")


async def delete_objects_by_prefix(bucket_name: str, prefix: str) -> Dict[str, Any]:
    """
    Delete all S3 objects under a given prefix.
    
    Uses S3's delete_objects API which can delete up to 1000 objects per request.
    Handles pagination for prefixes with more than 1000 objects.
    
    Args:
        bucket_name: The S3 bucket name
        prefix: The prefix (folder path) to delete objects from
        
    Returns:
        Dict with:
            - deleted_count: Number of objects successfully deleted
            - failed_count: Number of objects that failed to delete
            - errors: List of error messages
    """
    result = {
        "deleted_count": 0,
        "failed_count": 0,
        "errors": []
    }
    
    try:
        s3_client, _ = _get_s3_client_for_bucket(bucket_name)
        
        # Use paginator to handle large number of objects
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            # Prepare objects for deletion (max 1000 per request)
            objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
            
            if not objects_to_delete:
                continue
            
            # Delete objects in batch
            try:
                response = s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={
                        'Objects': objects_to_delete,
                        'Quiet': False  # Get detailed response
                    }
                )
                
                # Count successful deletions
                if 'Deleted' in response:
                    result["deleted_count"] += len(response['Deleted'])
                
                # Track failures
                if 'Errors' in response:
                    for error in response['Errors']:
                        result["failed_count"] += 1
                        result["errors"].append(f"{error['Key']}: {error['Message']}")
                        
            except Exception as batch_error:
                result["failed_count"] += len(objects_to_delete)
                result["errors"].append(f"Batch delete failed: {str(batch_error)}")
                logger.error(f"Batch delete failed for prefix {prefix}: {str(batch_error)}")
        
        logger.info(f"S3 cleanup for {bucket_name}/{prefix}: deleted={result['deleted_count']}, failed={result['failed_count']}")

    except Exception as e:
        error_msg = f"Failed to delete objects with prefix {prefix}: {str(e)}"
        result["errors"].append(error_msg)
        logger.error(error_msg)

    return result


# ============================================================================
# Folder Upload S3 Utilities
# ============================================================================

def get_folder_upload_prefix(project_id: str, upload_id: str) -> str:
    """
    Generate the S3 prefix for a folder upload.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID

    Returns:
        S3 prefix string (e.g., "artifacts/proj-123/folders/upload-456/")
    """
    return f"artifacts/{project_id}/folders/{upload_id}/"


def get_folder_file_s3_key(
    project_id: str,
    upload_id: str,
    relative_path: str
) -> str:
    """
    Generate the S3 key for a file within a folder upload.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID
        relative_path: The file's relative path within the folder

    Returns:
        Full S3 key (e.g., "artifacts/proj-123/folders/upload-456/files/src/Button.tsx")
    """
    clean_path = relative_path.lstrip('/').replace('//', '/')
    if '..' in Path(clean_path).parts:
        raise ValueError("Path traversal detected in relative path")
    prefix = get_folder_upload_prefix(project_id, upload_id)
    return f"{prefix}files/{clean_path}"


async def upload_folder_file(
    file_data: bytes,
    project_id: str,
    upload_id: str,
    relative_path: str,
    content_type: str = 'application/octet-stream'
) -> Dict[str, Any]:
    """
    Upload a single file to S3 as part of a folder upload.

    Args:
        file_data: The file contents as bytes
        project_id: The project ID
        upload_id: The folder upload ID
        relative_path: The file's relative path within the folder
        content_type: MIME type of the file

    Returns:
        Dict with s3_bucket, s3_key, s3_url, and checksum (SHA-256)
    """
    s3_client, s3_bucket, s3_region = await get_s3_client()

    s3_key = get_folder_file_s3_key(project_id, upload_id, relative_path)

    # Calculate SHA-256 checksum (stronger than MD5)
    checksum = hashlib.sha256(file_data).hexdigest()

    try:
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=file_data,
            ContentType=content_type,
            Metadata={
                'relative-path': relative_path,
                'upload-id': upload_id,
                'checksum-sha256': checksum
            }
        )

        # Generate URL
        s3_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"

        logger.debug(f"Uploaded file to S3: {s3_key}")

        return {
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "checksum": checksum  # SHA-256 hash
        }

    except ClientError as e:
        logger.error(f"Failed to upload file to S3: {s3_key}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )


async def upload_folder_manifest(
    project_id: str,
    upload_id: str,
    manifest_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Upload the folder manifest JSON to S3.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID
        manifest_data: The manifest dictionary

    Returns:
        Dict with s3_bucket, s3_key, s3_url
    """
    s3_client, s3_bucket, s3_region = await get_s3_client()

    prefix = get_folder_upload_prefix(project_id, upload_id)
    s3_key = f"{prefix}manifest.json"

    manifest_json = json.dumps(manifest_data, indent=2, default=str)

    try:
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=manifest_json.encode('utf-8'),
            ContentType='application/json'
        )

        s3_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"

        logger.info(f"Uploaded folder manifest to S3: {s3_key}")

        return {
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "s3_url": s3_url
        }

    except ClientError as e:
        logger.error(f"Failed to upload manifest to S3: {s3_key}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload manifest to storage"
        )


async def generate_presigned_download_url(
    s3_key: str,
    expiration: int = PRESIGNED_URL_EXPIRATION,
    filename: Optional[str] = None
) -> str:
    """
    Generate a presigned URL for downloading a file from S3.

    Args:
        s3_key: The S3 key of the file
        expiration: URL expiration time in seconds (default 1 hour)
        filename: Optional filename for Content-Disposition header

    Returns:
        Presigned URL string
    """
    s3_client, s3_bucket, _ = await get_s3_client()

    params = {
        'Bucket': s3_bucket,
        'Key': s3_key
    }

    # Add Content-Disposition if filename provided (sanitize to prevent header injection)
    if filename:
        safe_filename = re.sub(r'[^a-zA-Z0-9\s._-]', '_', filename)
        if not safe_filename or safe_filename.isspace():
            safe_filename = 'download'
        safe_filename = urllib.parse.quote(safe_filename, safe='')
        params['ResponseContentDisposition'] = f'attachment; filename="{safe_filename}"'

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=expiration
        )
        return url

    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )


async def delete_folder_file(
    project_id: str,
    upload_id: str,
    relative_path: str
) -> bool:
    """
    Delete a single file from a folder upload in S3.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID
        relative_path: The file's relative path

    Returns:
        True if deletion was successful
    """
    s3_client, s3_bucket, _ = await get_s3_client()

    s3_key = get_folder_file_s3_key(project_id, upload_id, relative_path)

    try:
        s3_client.delete_object(
            Bucket=s3_bucket,
            Key=s3_key
        )
        logger.info(f"Deleted file from S3: {s3_key}")
        return True

    except ClientError as e:
        logger.error(f"Failed to delete file from S3: {s3_key}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file from storage"
        )


async def delete_folder_upload(project_id: str, upload_id: str) -> Dict[str, Any]:
    """
    Delete all files associated with a folder upload from S3.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID

    Returns:
        Dict with deletion statistics
    """
    s3_client, s3_bucket, _ = await get_s3_client()

    prefix = get_folder_upload_prefix(project_id, upload_id)

    return await delete_objects_by_prefix(s3_bucket, prefix)


async def get_file_metadata(s3_key: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a file in S3.

    Args:
        s3_key: The S3 key of the file

    Returns:
        Dict with file metadata or None if not found
    """
    s3_client, s3_bucket, _ = await get_s3_client()

    try:
        response = s3_client.head_object(
            Bucket=s3_bucket,
            Key=s3_key
        )

        return {
            "content_length": response.get('ContentLength', 0),
            "content_type": response.get('ContentType', 'application/octet-stream'),
            "last_modified": response.get('LastModified'),
            "etag": response.get('ETag', '').strip('"'),
            "metadata": response.get('Metadata', {})
        }

    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        logger.error(f"Failed to get file metadata for {s3_key}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file metadata: {str(e)}"
        )


async def list_folder_files(
    project_id: str,
    upload_id: str,
    path_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all files in a folder upload from S3.

    Args:
        project_id: The project ID
        upload_id: The folder upload ID
        path_filter: Optional path prefix to filter files

    Returns:
        List of file metadata dicts
    """
    s3_client, s3_bucket, _ = await get_s3_client()

    prefix = get_folder_upload_prefix(project_id, upload_id) + "files/"
    if path_filter:
        prefix += path_filter.lstrip('/')

    files = []

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=s3_bucket, Prefix=prefix)

        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                # Extract relative path from S3 key
                s3_key = obj['Key']
                files_prefix = get_folder_upload_prefix(project_id, upload_id) + "files/"
                relative_path = s3_key[len(files_prefix):] if s3_key.startswith(files_prefix) else s3_key

                files.append({
                    "s3_key": s3_key,
                    "relative_path": relative_path,
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat() if obj.get('LastModified') else None,
                    "etag": obj.get('ETag', '').strip('"')
                })

        return files

    except ClientError as e:
        logger.error(f"Failed to list folder files for {project_id}/{upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

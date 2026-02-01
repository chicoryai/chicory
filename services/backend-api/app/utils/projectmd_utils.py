import os
import io
import logging
from typing import Optional
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from typing import Optional
from .s3_utils import get_s3_client

# Configure logging
logger = logging.getLogger(__name__)

def get_documentation_agent_id() -> Optional[str]:
    """Get the documentation agent ID from environment variable"""
    return os.getenv("DOCUMENTATION_AGENT_ID")

def get_documentation_agent_project_id() -> Optional[str]:
    """Get the documentation agent project ID from environment variable"""
    return os.getenv("DOCUMENTATION_AGENT_PROJECT_ID")


async def upload_projectmd_to_s3(project_md_content: str, project_id: str, training_id: str) -> str:
    """
    Upload project.md content to S3 following the path structure: {project_id}/{training_id}/project.md
    
    Args:
        project_md_content: The generated project.md content as string
        project_id: Project ID for S3 path
        training_id: Training ID for S3 path
        
    Returns:
        S3 URL of the uploaded file
    """
    s3_client, s3_bucket, s3_region = await get_s3_client()
    
    # Create S3 key following the simplified path structure
    s3_key = f"artifacts/{project_id}/projectmds/{training_id}/project.md"
    
    try:
        # Convert string content to bytes
        content_bytes = project_md_content.encode('utf-8')
        file_io = io.BytesIO(content_bytes)
        
        # Upload to S3 with markdown content type
        s3_client.upload_fileobj(
            file_io,
            s3_bucket,
            s3_key,
            ExtraArgs={'ContentType': 'text/markdown'}
        )

        # Generate S3 URL - use s3:// format for consistency
        # This works for both MinIO and AWS S3 when downloaded via SDK
        s3_url = f"s3://{s3_bucket}/{s3_key}"

        logger.info(f"Successfully uploaded project.md to S3: {s3_url}")
        return s3_url
        
    except Exception as e:
        logger.error(f"Error uploading project.md to S3: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload project.md to S3: {str(e)}"
        )

def generate_s3_url(project_id: str, training_id: str) -> str:
    """
    Generate the expected S3 URL for a project.md file without uploading

    Args:
        project_id: Project ID
        training_id: Training ID

    Returns:
        Expected S3 URL in s3:// format (works for both MinIO and AWS)
    """
    s3_bucket = os.getenv("S3_BUCKET_NAME")

    if not s3_bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 bucket not configured"
        )

    s3_key = f"artifacts/{project_id}/projectmds/{training_id}/project.md"
    return f"s3://{s3_bucket}/{s3_key}"

async def download_projectmd_from_s3(project_id: str, training_id: str) -> str:
    """
    Download project.md content from S3
    
    Args:
        project_id: Project ID
        training_id: Training ID
        
    Returns:
        Project.md content as string
    """
    s3_client, s3_bucket, s3_region = await get_s3_client()
    
    s3_key = f"artifacts/{project_id}/projectmds/{training_id}/project.md"
    
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        
        logger.info(f"Successfully downloaded project.md from S3: {s3_key}")
        return content
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"project.md not found for training {training_id}"
            )
        else:
            logger.error(f"Error downloading project.md from S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download project.md from S3: {str(e)}"
            )
    except Exception as e:
        logger.error(f"Error downloading project.md from S3: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download project.md from S3: {str(e)}"
        )

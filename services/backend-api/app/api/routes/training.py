from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import PlainTextResponse
from typing import List, Dict, Any
from app.models.training import Training, TrainingCreate, TrainingResponse, TrainingList, TrainingUpdate
from app.models.project import Project
from app.models.agent import Agent
from datetime import datetime, timezone
import logging
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse
from app.utils.s3_utils import _get_s3_client_for_bucket
from app.utils.rabbitmq_client import queue_training_job
from app.utils.documentation_agent import get_or_create_documentation_agent
from app.utils.projectmd_orchestration import start_projectmd_orchestration

router = APIRouter()

@router.post("/projects/{project_id}/training", response_model=TrainingResponse, status_code=status.HTTP_201_CREATED)
async def create_training_job(project_id: str, training_data: TrainingCreate, background_tasks: BackgroundTasks):
    """Start a new training job for a project"""
    # Verify the project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Create new training job
    new_training = Training(
        project_id=project_id,
        data_source_ids=training_data.data_source_ids,
        description=training_data.description,
        status="queued"
    )
    
    # Save to database
    await new_training.insert()
    
    # Add job to background queue
    background_tasks.add_task(queue_training_job, new_training.id, project_id, project.name, training_data.data_source_ids)
    
    # Format the response
    return TrainingResponse(
        id=new_training.id,
        project_id=new_training.project_id,
        data_source_ids=new_training.data_source_ids,
        status=new_training.status,
        description=new_training.description,
        progress=new_training.progress,
        error=new_training.error,
        created_at=new_training.created_at.isoformat(),
        updated_at=new_training.updated_at.isoformat()
    )

@router.get("/projects/{project_id}/training/{training_id}", response_model=TrainingResponse)
async def get_training_job(project_id: str, training_id: str):
    """Get the status of a training job"""
    # Find the training job
    training = await Training.find_one({"_id": training_id, "project_id": project_id})
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job with ID {training_id} not found for project {project_id}"
        )
    
    # Format the response
    return TrainingResponse(
        id=training.id,
        project_id=training.project_id,
        data_source_ids=training.data_source_ids,
        status=training.status,
        description=training.description,
        progress=training.progress,
        error=training.error,
        created_at=training.created_at.isoformat(),
        updated_at=training.updated_at.isoformat(),
        projectmd_generation={
            "status": training.projectmd_status,
            "documentation_agent_id": training.projectmd_documentation_agent_id,
            "documentation_project_id": training.projectmd_documentation_project_id,
            "s3_url": training.projectmd_s3_url,
            "error_message": training.projectmd_error_message,
            "started_at": training.projectmd_started_at.isoformat() if training.projectmd_started_at else None,
            "completed_at": training.projectmd_completed_at.isoformat() if training.projectmd_completed_at else None
        } if training.projectmd_status else None
    )

@router.get("/projects/{project_id}/training", response_model=TrainingList)
async def list_training_jobs(project_id: str):
    """List all training jobs for a project"""
    # Verify the project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Find all training jobs for this project
    training_jobs = await Training.find({"project_id": project_id}).to_list()
    
    # Format the response
    training_responses = [
        TrainingResponse(
            id=job.id,
            project_id=job.project_id,
            data_source_ids=job.data_source_ids,
            status=job.status,
            description=job.description,
            progress=job.progress,
            error=job.error,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            projectmd_generation={
                "status": job.projectmd_status,
                "documentation_agent_id": job.projectmd_documentation_agent_id,
                "documentation_project_id": job.projectmd_documentation_project_id,
                "s3_url": job.projectmd_s3_url,
                "error_message": job.projectmd_error_message,
                "started_at": job.projectmd_started_at.isoformat() if job.projectmd_started_at else None,
                "completed_at": job.projectmd_completed_at.isoformat() if job.projectmd_completed_at else None
            } if job.projectmd_status else None
        ) for job in training_jobs
    ]
    
    return TrainingList(training_jobs=training_responses)


@router.put("/projects/{project_id}/training/{training_id}", response_model=TrainingResponse)
async def update_training_job(project_id: str, training_id: str, training_update: TrainingUpdate):
    """Update a training job"""
    # Find the training job
    training = await Training.find_one({"_id": training_id, "project_id": project_id})
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job with ID {training_id} not found for project {project_id}"
        )
    
    # Prepare update data
    update_data = training_update.dict(exclude_unset=True)
    
    # Only process non-empty updates
    if update_data:
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update the training job
        await training.update({"$set": update_data})
        
        # Refresh the training data by fetching it again
        training = await Training.find_one({"_id": training_id, "project_id": project_id})
    
    # Format the response
    return TrainingResponse(
        id=training.id,
        project_id=training.project_id,
        data_source_ids=training.data_source_ids,
        status=training.status,
        description=training.description,
        progress=training.progress,
        error=training.error,
        created_at=training.created_at.isoformat(),
        updated_at=training.updated_at.isoformat()
    )


@router.delete("/projects/{project_id}/training/{training_id}", status_code=status.HTTP_200_OK)
async def delete_training_job(project_id: str, training_id: str):
    """Delete a training job"""
    # Find the training job
    training = await Training.find_one({"_id": training_id, "project_id": project_id})
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job with ID {training_id} not found for project {project_id}"
        )
    
    # Check if the training job is in progress
    if training.status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete training job {training_id} because it is currently in progress"
        )
    
    # Delete the training job
    await training.delete()
    
    # Return success message
    return {
        "message": f"Training job {training_id} successfully deleted",
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/projects/{project_id}/training/{training_id}/projectmd", response_model=TrainingResponse, status_code=status.HTTP_201_CREATED)
async def generate_project_md(project_id: str, training_id: str, background_tasks: BackgroundTasks):
    """Start project.md generation for a training job"""
    # Verify the project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Verify the training job exists and belongs to the project
    training = await Training.find_one({"_id": training_id, "project_id": project_id})
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job with ID {training_id} not found for project {project_id}"
        )
    
    # Check if project.md generation is already in progress or completed
    if training.projectmd_status in ["queued", "in_progress"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project.md generation is already {training.projectmd_status} for training {training_id}"
        )

    # Get or create documentation agent for this project (lazy creation with atomic upsert)
    documentation_agent_id, documentation_project_id = await get_or_create_documentation_agent(project_id)
    
    # Update training job with project.md generation status
    update_data = {
        "projectmd_status": "queued",
        "projectmd_documentation_agent_id": documentation_agent_id,
        "projectmd_documentation_project_id": documentation_project_id,
        "projectmd_started_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await training.update({"$set": update_data})
    
    # Add background task for project.md generation orchestration
    # Pass training object directly to avoid unnecessary database read
    background_tasks.add_task(
        start_projectmd_orchestration, 
        training,
        documentation_agent_id,
        documentation_project_id
    )
    
    # Refresh training data
    training = await Training.find_one({"_id": training_id, "project_id": project_id})
    
    # Format the response
    return TrainingResponse(
        id=training.id,
        project_id=training.project_id,
        data_source_ids=training.data_source_ids,
        status=training.status,
        description=training.description,
        progress=training.progress,
        error=training.error,
        created_at=training.created_at.isoformat(),
        updated_at=training.updated_at.isoformat(),
        projectmd_generation={
            "status": training.projectmd_status,
            "documentation_agent_id": training.projectmd_documentation_agent_id,
            "documentation_project_id": training.projectmd_documentation_project_id,
            "s3_url": training.projectmd_s3_url,
            "error_message": training.projectmd_error_message,
            "started_at": training.projectmd_started_at.isoformat() if training.projectmd_started_at else None,
            "completed_at": training.projectmd_completed_at.isoformat() if training.projectmd_completed_at else None
        } if training.projectmd_status else None
    )


@router.get("/projects/{project_id}/training/latest/projectmd", response_class=PlainTextResponse)
async def get_latest_project_md(project_id: str):
    """Get the project.md content from the latest training run"""
    # Verify the project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Find the latest training job for this project that has completed project.md generation
    training = await Training.find_one(
        {
            "project_id": project_id,
            "projectmd_status": "completed",
            "projectmd_s3_url": {"$exists": True, "$ne": None}
        },
        sort=[("projectmd_completed_at", -1)]
    )
    
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed project.md found for project {project_id}"
        )
    
    # Get the S3 URL and extract bucket and key
    s3_url = training.projectmd_s3_url
    
    # Parse both s3:// and https:// URL formats
    if s3_url.startswith("s3://"):
        # Parse S3 URL: s3://bucket-name/key/path
        s3_parts = s3_url[5:].split("/", 1)
        if len(s3_parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid S3 URL format"
            )
        bucket_name = s3_parts[0]
        object_key = s3_parts[1]
    elif s3_url.startswith("https://"):
        # Parse HTTPS URL: https://bucket-name.s3.region.amazonaws.com/key/path
        parsed_url = urlparse(s3_url)
        hostname = parsed_url.hostname
        
        # Extract bucket name from hostname (format: bucket-name.s3.region.amazonaws.com)
        if hostname and ".s3." in hostname and ".amazonaws.com" in hostname:
            bucket_name = hostname.split(".s3.")[0]
            object_key = parsed_url.path.lstrip("/")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid S3 HTTPS URL format"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid S3 URL format. Must start with s3:// or https://"
        )
    
    # Download the content from S3
    try:
        s3_client, _ = _get_s3_client_for_bucket(bucket_name)
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')
        
        return PlainTextResponse(content=content)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project.md file not found in S3: {s3_url}"
            )
        elif error_code == 'NoSuchBucket':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"S3 bucket not found: {bucket_name}"
            )
        else:
            logging.error(f"Error downloading project.md from S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve project.md from S3: {str(e)}"
            )
    except Exception as e:
        logging.error(f"Unexpected error retrieving project.md: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project.md: {str(e)}"
        )

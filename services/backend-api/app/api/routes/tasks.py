from typing import List, Optional, Dict, Any
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
from datetime import datetime
import os
import mimetypes

import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Redis imports for streaming
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster

from app.models.agent import Agent
from app.models.tasks import (
    Task, TaskCreate, TaskResponse, TaskList,
    TaskRole, TaskStatus, TaskChunk, TaskComplete, TaskFeedback
)
from app.utils.rabbitmq_client import queue_agent_task
from app.utils.task_limits import active_task_details

router = APIRouter()

# Redis client for streaming (lazy initialization)
_redis_client: Optional[redis.Redis | RedisCluster] = None

async def get_redis_client() -> redis.Redis | RedisCluster:
    """
    Redis client (async) that works with both standalone and cluster Redis instances.
    Automatically detects the Redis mode and uses the appropriate client.
    """
    global _redis_client
    if _redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            print(f"Initializing Redis client with URL: {redis_url}")

            # SSL configuration
            ssl_enabled = redis_url.startswith("rediss://")
            ssl_ca_certs = os.getenv("REDIS_SSL_CA_CERTS", "/etc/ssl/certs/ca-certificates.crt")
            ssl_cert_file = os.getenv("REDIS_SSL_CERT_FILE")
            ssl_key_file = os.getenv("REDIS_SSL_KEY_FILE")

            # First try to connect as standalone Redis
            try:
                # Build connection parameters
                connection_params = {
                    "socket_connect_timeout": 3,
                    "socket_timeout": 2,
                    "health_check_interval": 30,
                    "max_connections": 100,
                    "decode_responses": True,
                }
                
                # Only add SSL parameters if SSL is enabled
                if ssl_enabled:
                    connection_params.update({
                        "ssl": True,
                        "ssl_cert_reqs": "required",
                        "ssl_ca_certs": ssl_ca_certs,
                    })
                    if ssl_cert_file:
                        connection_params["ssl_certfile"] = ssl_cert_file
                    if ssl_key_file:
                        connection_params["ssl_keyfile"] = ssl_key_file
                
                _redis_client = redis.from_url(redis_url, **connection_params)
                
                await _redis_client.ping()
                print("Redis standalone connection successful!")
                
            except Exception as standalone_error:
                print(f"Standalone Redis connection failed: {standalone_error}")
                print("Trying Redis cluster mode...")
                
                # If standalone fails, try cluster mode
                cluster_params = {
                    "socket_connect_timeout": 3,
                    "socket_timeout": 2,
                    "health_check_interval": 30,
                    "max_connections": 100,
                    "decode_responses": True,
                }
                
                # Only add SSL parameters if SSL is enabled
                if ssl_enabled:
                    cluster_params.update({
                        "ssl": True,
                        "ssl_cert_reqs": "required",
                        "ssl_ca_certs": ssl_ca_certs,
                    })
                    if ssl_cert_file:
                        cluster_params["ssl_certfile"] = ssl_cert_file
                    if ssl_key_file:
                        cluster_params["ssl_keyfile"] = ssl_key_file
                
                _redis_client = RedisCluster.from_url(redis_url, **cluster_params)
                
                await _redis_client.ping()
                print("Redis cluster connection successful!")
            
        except Exception as e:
            print(f"Failed to initialize Redis client: {e}")
            print(f"Redis URL: {redis_url}")
            print(f"Error type: {type(e).__name__}")
            _redis_client = None
            
    return _redis_client

async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

# Task endpoints
@router.post("/projects/{project_id}/agents/{agent_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(project_id: str, agent_id: str, task_data: TaskCreate, background_tasks: BackgroundTasks):
    """Create a new task in a agent with project-level context"""
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Check if there are any active tasks for this project and agent
    active_task_count, has_active_tasks = await active_task_details(project_id, agent_id)
    if has_active_tasks:
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limited: Agent already has {active_task_count} active task(s). Please wait for completion before submitting new tasks."
        )
    
    # Create the user task
    task = Task(
        agent_id=agent_id,
        project_id=project_id,  # Explicitly set project_id from URL parameter
        role=TaskRole.USER,
        content=task_data.content,
        status=TaskStatus.QUEUED,
        metadata=task_data.metadata or {}
    )
    # Save the task
    await task.save()
    
    # Verify the task has a valid ID after save
    if not task.id:
        raise HTTPException(status_code=500, detail="Failed to create task - no ID generated")
    
    # Create an assistant task that will be filled in later
    assistant_task = Task(
        agent_id=agent_id,
        project_id=project_id,  # Explicitly set project_id from URL parameter
        role=TaskRole.ASSISTANT,
        content="",  # Will be populated by the worker
        status=TaskStatus.QUEUED,
        related_task_id=str(task.id),  # Directly link to the user task using first-class property
        metadata={}
    )
    # Save the assistant task
    await assistant_task.save()
    
    # Verify the assistant task has a valid ID after save
    if not assistant_task.id:
        raise HTTPException(status_code=500, detail="Failed to create assistant task - no ID generated")
    
    # Update the user task to include a reference to the assistant task using the first-class property
    task.related_task_id = str(assistant_task.id)
    await task.save()
    
    # Update task count
    agent.task_count += 2  # User task + assistant task
    agent.updated_at = datetime.utcnow()
    await agent.update({"$set": {"task_count": agent.task_count, "updated_at": agent.updated_at}})
    
    # Add task to RabbitMQ for processing using the dedicated queue function
    # This runs as a background task to avoid blocking the API response
    background_tasks.add_task(
        queue_agent_task,
        task_id=task.id,
        assistant_task_id=assistant_task.id,
        agent_id=agent_id,
        project_id=project_id,
        content=task_data.content,
        metadata=task_data.metadata
    )
    
    # Update task with queue information
    task.metadata["queue_info"] = {
        "queue_name": "agent_tasks",
        "task_id": f"amq-{task.id}"
    }
    await task.save()
        
    # Ensure the project_id is set correctly for the response
    actual_project_id = task.project_id if task.project_id else project_id
    print(f"DEBUG: Final task ID: {task.id}, project_id: {actual_project_id}")
    
    # Convert Task document to TaskResponse object explicitly to handle _id aliasing
    return TaskResponse(
        id=str(task.id),
        agent_id=task.agent_id,
        project_id=actual_project_id,  # Use the validated project_id
        role=task.role.value if task.role else None,
        content=task.content,
        status=task.status.value if task.status else None,
        related_task_id=task.related_task_id,
        metadata=task.metadata,
        created_at=task.created_at,
        completed_at=task.completed_at
    )

@router.get("/projects/{project_id}/agents/{agent_id}/tasks", response_model=TaskList)
async def get_tasks(
    project_id: str,
    agent_id: str,
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    status: Optional[list[str]] = Query(None, description="Filter tasks by status (e.g. 'queued', 'processing', 'completed', 'failed')")
):
    """
    Get tasks from an agent
    
    Args:
        project_id: ID of the project
        agent_id: ID of the agent to get tasks from
        limit: Maximum number of tasks to return (1-100)
        sort_order: Sort direction ('asc' for oldest to newest, 'desc' for newest to oldest)
        status: Optional list of statuses to filter tasks by
    """
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
        
    # Build query with agent_id and optional status filter
    query = {"agent_id": agent_id}
    
    # Add status filter if provided
    if status:
        # Convert status values to TaskStatus enum values if needed
        valid_statuses = [s for s in status if s in [ts.value for ts in TaskStatus]]
        if valid_statuses:
            query["status"] = {"$in": valid_statuses}
    
    # Get tasks for this agent with pagination support
    # Sort by creation date (default: oldest to newest)
    sort_direction = 1 if sort_order.lower() == "asc" else -1
    tasks = await Task.find(query).sort([("created_at", sort_direction)]).skip(skip).limit(limit + 1).to_list()
    
    # Check if there are more tasks
    has_more = len(tasks) > limit
    if has_more:
        tasks = tasks[:limit]
    
    # Convert Task documents to TaskResponse objects explicitly to handle _id aliasing
    task_responses = [
        TaskResponse(
            id=str(task.id),
            agent_id=task.agent_id,
            project_id=task.project_id,
            role=task.role.value if task.role else None,
            content=task.content,
            status=task.status.value if task.status else None,
            related_task_id=task.related_task_id,
            metadata=task.metadata,
            created_at=task.created_at,
            completed_at=task.completed_at
        ) for task in tasks
    ]
    
    return TaskList(tasks=task_responses, has_more=has_more)

@router.get("/projects/{project_id}/agents/{agent_id}/tasks/{task_id}", response_model=TaskResponse)
async def get_task(project_id: str, agent_id: str, task_id: str):
    """Get a specific task"""
    task = await Task.get(task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get the agent to validate project ownership
    agent = await Agent.get(agent_id)
    if not agent or agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Ensure the project_id is set correctly for the response
    actual_project_id = task.project_id if task.project_id else project_id
    print(f"DEBUG: Final task ID: {task.id}, project_id: {actual_project_id}")
    
    # Convert Task document to TaskResponse object explicitly to handle _id aliasing
    return TaskResponse(
        id=str(task.id),
        agent_id=task.agent_id,
        project_id=actual_project_id,  # Use the validated project_id
        role=task.role.value if task.role else None,
        content=task.content,
        status=task.status.value if task.status else None,
        related_task_id=task.related_task_id,
        metadata=task.metadata,
        created_at=task.created_at,
        completed_at=task.completed_at
    )

@router.put("/projects/{project_id}/agents/{agent_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: str, 
    agent_id: str, 
    task_id: str, 
    task_update: Dict[str, Any]
):
    """Update a task status and/or content"""
    # Get the task to update
    task = await Task.get(task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get the agent to validate project ownership
    agent = await Agent.get(agent_id)
    if not agent or agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Prepare update data
    update_data = {}
    
    # Update status if provided
    if 'status' in task_update:
        # Validate status
        try:
            status = TaskStatus(task_update['status'])
            update_data['status'] = status
            # Set completed_at timestamp if status is COMPLETED
            if status == TaskStatus.COMPLETED:
                update_data['completed_at'] = datetime.utcnow()
                
                # Add audit trail path for completed tasks
                if task.role == TaskRole.ASSISTANT:
                    audit_bucket = os.environ.get('TASK_AUDIT_TRAIL_S3_BUCKET_NAME', 'chicory-agents-audit-trails')
                    
                    audit_path = f"s3://{audit_bucket}/{project_id.lower()}/{agent_id.lower()}/{task.id}/messages.json"
                    artifacts_prefix = f"{project_id.lower()}/{agent_id.lower()}/{task.id}/artifacts/"
                    if 'metadata' not in update_data:
                        update_data['metadata'] = task.metadata or {}
                    update_data['metadata']['audit_trail'] = audit_path
                    update_data['metadata']['artifacts_prefix'] = artifacts_prefix
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {task_update['status']}. Valid statuses are: {[s.value for s in TaskStatus]}")
    
    # Update content if provided
    if 'content' in task_update:
        update_data['content'] = task_update['content']
    
    # Update timestamp
    update_data['updated_at'] = datetime.utcnow()
    
    # Update the task
    if update_data:
        await task.update({"$set": update_data})
        # Apply updates to the local object to reflect the database state
        for key, value in update_data.items():
            setattr(task, key, value)
    
    # Return the updated task
    return TaskResponse(
        id=str(task.id),
        agent_id=task.agent_id,
        project_id=task.project_id,
        role=task.role.value if task.role else None,
        content=task.content,
        status=task.status.value if task.status else None,
        related_task_id=task.related_task_id,
        metadata=task.metadata,
        created_at=task.created_at,
        completed_at=task.completed_at
    )

@router.get("/projects/{project_id}/agents/{agent_id}/tasks/{task_id}/artifacts")
async def list_task_artifacts(project_id: str, agent_id: str, task_id: str):
    """List artifacts generated by a task and return presigned download URLs."""
    task = await Task.get(task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Task not found")

    agent = await Agent.get(agent_id)
    if not agent or agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")

    bucket_name = os.environ.get('TASK_AUDIT_TRAIL_S3_BUCKET_NAME')
    if not bucket_name:
        return {"artifacts": []}

    prefix = f"{project_id.lower()}/{agent_id.lower()}/{task_id}/artifacts/"

    try:
        s3_client = boto3.client('s3', region_name=os.getenv("AWS_REGION", "us-west-2"))

        artifacts = []
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                filename = key[len(prefix):]  # relative path after artifacts/
                if not filename:
                    continue

                # Generate presigned URL (valid for 1 hour)
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': key},
                    ExpiresIn=3600
                )

                content_type, _ = mimetypes.guess_type(filename)
                artifacts.append({
                    "filename": filename,
                    "size": obj.get('Size', 0),
                    "last_modified": obj['LastModified'].isoformat() if obj.get('LastModified') else None,
                    "download_url": presigned_url,
                    "content_type": content_type or "application/octet-stream",
                })

        return {"artifacts": artifacts}

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            return {"artifacts": []}
        logger.error(f"S3 ClientError listing artifacts for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list artifacts")
    except Exception as e:
        logger.error(f"Error listing artifacts for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list artifacts")


@router.delete("/projects/{project_id}/agents/{agent_id}/tasks/{task_id}", response_model=Dict[str, str])
async def delete_task(project_id: str, agent_id: str, task_id: str):
    """Delete a task"""
    task = await Task.get(task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get the agent to validate project ownership
    agent = await Agent.get(agent_id)
    if not agent or agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Delete the task
    await task.delete()
    
    # Update task count in agent
    agent.task_count = max(0, agent.task_count - 1)  # Ensure it doesn't go below 0
    agent.updated_at = datetime.utcnow()
    await agent.update({"$set": {"task_count": agent.task_count, "updated_at": agent.updated_at}})
    
    return {"task": "Task deleted successfully"}

@router.get("/projects/{project_id}/agents/{agent_id}/tasks/{task_id}/stream")
async def stream_specific_task(request: Request, project_id: str, agent_id: str, task_id: str):
    """Stream updates for a specific task using Server-Sent Events"""
    # Verify agent exists and belongs to the project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Get the specific task by ID
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Validate that the task belongs to the specified agent and project
    if task.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Task does not belong to the specified agent")
        
    if task.project_id != project_id:
        raise HTTPException(status_code=400, detail="Task does not belong to the specified project")
    
    # Validate that it's an assistant task that can be streamed
    if task.role != TaskRole.ASSISTANT:
        raise HTTPException(status_code=400, detail="Only assistant tasks can be streamed")
        
    async def event_generator():
        # Initial empty task to establish the connection
        yield {
            "event": "message_start",
            "data": json.dumps({
                "id": task.id,
                "agent_id": agent_id,
                "role": "assistant"
            })
        }
        
        # Get Redis client for streaming
        redis_client = await get_redis_client()
        
        # Poll both Redis streams and database for updates
        poll_interval = 0.5  # seconds
        max_poll_time = 120  # seconds (2 minutes timeout)
        total_poll_time = 0
        last_content = None  # Track last sent content
        last_redis_id = "0"  # Track last Redis stream message ID
        
        while total_poll_time < max_poll_time:
            if await request.is_disconnected():
                print(f"Client disconnected while streaming task {task_id}")
                break
                
            # Check Redis stream for Claude Code messages if Redis is available
            if redis_client:
                try:
                    stream_key = f"task_stream:{task_id}"
                    # Read new messages from Redis stream
                    streams = await redis_client.xread({stream_key: last_redis_id}, count=10, block=100)
                    
                    for stream_name, messages in streams:
                        for message_id, fields in messages:
                            # Update last processed Redis message ID
                            last_redis_id = message_id
                            
                            # Parse the Redis stream message with structured data
                            message_type = fields.get("message_type", "")
                            timestamp = fields.get("timestamp", "")
                            raw_message = fields.get("message", "")
                            structured_data_str = fields.get("structured_data", "{}")
                            
                            # Parse structured data
                            try:
                                structured_data = json.loads(structured_data_str) if structured_data_str else {}
                            except json.JSONDecodeError:
                                structured_data = {}
                            
                            # Send Claude Code streaming events with both formats
                            yield {
                                "event": "claude_code_message",
                                "data": json.dumps({
                                    "id": task_id,
                                    "message_id": message_id,
                                    "message_type": message_type,
                                    "message": raw_message,
                                    "timestamp": timestamp,
                                    "structured_data": structured_data
                                })
                            }
                            
                except Exception as e:
                    # Redis error - continue with database polling only
                    print(f"Redis streaming error for task {task_id}: {e}")
                
            # Get the latest version of the task from the database
            current_msg = await Task.get(task_id)
            if not current_msg:
                print(f"Task {task_id} no longer exists")
                break

            # Get current content
            current_content = current_msg.content or ""
            
            # Only send updates if content has changed
            if current_content != last_content:
                # Send the entire current content as one chunk
                yield {
                    "event": "message_chunk",
                    "data": json.dumps({
                        "id": task_id,
                        "content_chunk": current_content
                    })
                }
                # Update the last sent content
                last_content = current_content
            
            # If task is complete, send completion event and stop polling
            if current_msg.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                # Send completion event
                yield {
                    "event": "message_complete",
                    "data": json.dumps({
                        "id": task_id,
                        "status": current_msg.status.value,
                        "completed_at": current_msg.completed_at.isoformat() if current_msg.completed_at else datetime.utcnow().isoformat()
                    })
                }
                break
            
            # Wait before polling again
            await asyncio.sleep(poll_interval)
            total_poll_time += poll_interval
        
        # If we reached the timeout without completion, send a timeout event
        if total_poll_time >= max_poll_time:
            print(f"Timeout reached while streaming task {task_id}")
            yield {
                "event": "task_timeout",
                "data": json.dumps({
                    "id": task_id,
                    "task": "Response generation timed out"
                })
            }
    
    return EventSourceResponse(event_generator())

@router.post("/projects/{project_id}/agents/{agent_id}/tasks/{task_id}/feedback", response_model=TaskResponse)
async def submit_task_feedback(project_id: str, agent_id: str, task_id: str, feedback_data: TaskFeedback):
    """Submit feedback for a specific task"""
    # Get the task to update
    task = await Task.get(task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get the agent to validate project ownership
    agent = await Agent.get(agent_id)
    if not agent or agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Initialize feedback in metadata if it doesn't exist
    if "feedback" not in task.metadata:
        task.metadata["feedback"] = []
    
    # Add the new feedback with timestamp
    feedback_entry = {
        "rating": feedback_data.rating,  # String: 'positive' or 'negative'
        "feedback": feedback_data.feedback,
        "tags": feedback_data.tags,
        "submitted_at": datetime.utcnow().isoformat()
    }
    task.metadata["feedback"].append(feedback_entry)
    
    # Update the task
    task.updated_at = datetime.utcnow()
    await task.save()
    
    # Return the updated task
    return TaskResponse(
        id=str(task.id),
        agent_id=task.agent_id,
        project_id=task.project_id,
        role=task.role.value if task.role else None,
        content=task.content,
        status=task.status.value if task.status else None,
        related_task_id=task.related_task_id,
        metadata=task.metadata,
        created_at=task.created_at,
        completed_at=task.completed_at
    )

@router.post("/projects/{project_id}/agents/{agent_id}/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(project_id: str, agent_id: str, task_id: str):
    """Cancel a task that is queued or processing"""
    # Get the task to cancel
    task = await Task.get(task_id)
    if not task or task.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get the agent to validate project ownership
    agent = await Agent.get(agent_id)
    if not agent or agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Check if task can be cancelled (only queued or processing tasks)
    if task.status not in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel task with status '{task.status.value}'. Only queued or processing tasks can be cancelled."
        )
    
    # Update task status to cancelled
    update_data = {
        'status': TaskStatus.CANCELLED,
        'completed_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    # Add cancellation metadata
    if 'metadata' not in task.metadata:
        task.metadata = {}
    task.metadata['cancelled_at'] = datetime.utcnow().isoformat()
    task.metadata['cancellation_reason'] = 'User requested cancellation'
    update_data['metadata'] = task.metadata
    
    # Update the task
    await task.update({"$set": update_data})
    
    # Apply updates to the local object to reflect the database state
    for key, value in update_data.items():
        setattr(task, key, value)
    
    # If there's a related task (assistant task), cancel it too
    if task.related_task_id:
        related_task = await Task.get(task.related_task_id)
        if related_task and related_task.status in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
            related_update_data = {
                'status': TaskStatus.CANCELLED,
                'completed_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            if 'metadata' not in related_task.metadata:
                related_task.metadata = {}
            related_task.metadata['cancelled_at'] = datetime.utcnow().isoformat()
            related_task.metadata['cancellation_reason'] = 'Related task was cancelled'
            related_update_data['metadata'] = related_task.metadata
            await related_task.update({"$set": related_update_data})
    
    # Return the cancelled task
    return TaskResponse(
        id=str(task.id),
        agent_id=task.agent_id,
        project_id=task.project_id,
        role=task.role.value if task.role else None,
        content=task.content,
        status=task.status.value if task.status else None,
        related_task_id=task.related_task_id,
        metadata=task.metadata,
        created_at=task.created_at,
        completed_at=task.completed_at
    )

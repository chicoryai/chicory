"""
ACP (Agent Communication Protocol) endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from pydantic import BaseModel
from datetime import datetime

from app.models.agent import Agent
from app.models.tasks import (
    Task, TaskCreate, TaskStatus, TaskRole
)
from app.api.routes.tasks import create_task
from app.utils.task_limits import active_task_details

router = APIRouter()

# ACP Protocol models
class MessagePart(BaseModel):
    content_type: str
    content: str

class Message(BaseModel):
    parts: List[MessagePart]
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class RunCreate(BaseModel):
    agent_name: str  # Using agent_name as per ACP spec, but this will contain agent ID
    session_id: Optional[str] = None
    session: Optional[Dict[str, Any]] = None
    input: List[Message]
    mode: Optional[str] = "async"  # sync, async, or stream
    
class Run(BaseModel):
    agent_name: str
    run_id: str
    status: str
    output: List[Message] = []
    created_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[Dict[str, Any]] = None

# ACP Protocol endpoints with versioning
@router.post("/api/v1/runs", response_model=Run, status_code=201)
async def create_run(
    run_data: RunCreate, 
    background_tasks: BackgroundTasks
):
    """
    Create and start a new run following ACP protocol
    
    This endpoint implements the ACP protocol POST /api/v1/runs endpoint
    which creates a new run for the specified agent
    """
    # Get the agent to verify it exists using agent_name field (which contains agent ID)
    agent_id = run_data.agent_name
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with ID '{agent_id}' not found")
    
    # Use the project from the agent
    project_id = agent.project_id
    
    # Check if there are any active tasks for this project and agent
    active_task_count, has_active_tasks = await active_task_details(project_id, agent_id)
    if has_active_tasks:
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limited: Agent already has {active_task_count} active task(s). Please wait for completion before submitting new requests."
        )
    
    # Ensure project_id is lowercase, consistent with the pattern in other services
    if project_id:
        project_id = project_id.lower()
    
    # Convert the ACP message to our content format
    # For simplicity, we concatenate all parts from all messages into a single content string
    content = ""
    for message in run_data.input:
        for part in message.parts:
            if part.content_type.startswith("text/"):
                content += part.content + "\n"
    
    # Create metadata with ACP-specific info
    metadata = {
        "acp": {
            "session_id": run_data.session_id,
            "mode": run_data.mode,
            "original_format": "acp",
            "version": "v1"
        }
    }
    
    # Create the task using our existing structure
    task_data = TaskCreate(
        content=content.strip(),
        metadata=metadata
    )
    
    # Call our existing create_task function to handle the task creation
    task_response = await create_task(project_id, agent_id, task_data, background_tasks)
    
    # Make sure we have a related_task_id (the assistant's task)
    if not task_response.related_task_id:
        raise HTTPException(status_code=500, detail="Failed to create assistant task")
    
    # Convert to ACP Run format
    run_status = "created"
    if task_response.status == "processing":
        run_status = "in-progress"
    elif task_response.status in ["completed", "failed"]:
        run_status = task_response.status
    
    # Return the response in ACP format using the assistant task ID as run_id
    return Run(
        agent_name=agent_id,  # Return agent_id in agent_name field
        run_id=task_response.related_task_id,
        status=run_status,
        output=[],  # Initially empty, will be populated when the task completes
        created_at=task_response.created_at
    )


@router.get("/api/v1/runs/{run_id}", response_model=Run)
async def get_run(run_id: str):
    """
    Get the current status and details of a run
    
    This endpoint implements the ACP protocol GET /api/v1/runs/{run_id} endpoint
    which returns the status and details of a run
    """
    # Get the task by the run_id
    # In our implementation, the run_id corresponds to the assistant's task ID
    assistant_task = await Task.get(run_id)
    if not assistant_task:
        raise HTTPException(status_code=404, detail=f"Run with id '{run_id}' not found")
    
    # Check if this is indeed an assistant task with a related_task_id pointing to a user task
    if assistant_task.role != TaskRole.ASSISTANT or not assistant_task.related_task_id:
        raise HTTPException(status_code=400, detail="Invalid run ID or not an assistant task")
    
    # Get the related user task that contains the input
    user_task = await Task.get(assistant_task.related_task_id)
    if not user_task:
        raise HTTPException(status_code=500, detail="Related user task not found")
    
    # Get the agent
    agent_id = assistant_task.agent_id
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=500, detail="Associated agent not found")
    
    # Project ID is determined by the agent's project
    
    # Convert task status to ACP run status
    status_mapping = {
        TaskStatus.QUEUED: "created",
        TaskStatus.PROCESSING: "in-progress",
        TaskStatus.COMPLETED: "completed",
        TaskStatus.FAILED: "failed"
    }
    acp_status = status_mapping.get(assistant_task.status, "in-progress")
    
    # Format the assistant task content as output
    output = []
    if assistant_task.content:
        output.append(
            Message(
                parts=[
                    MessagePart(
                        content_type="text/plain",
                        content=assistant_task.content
                    )
                ],
                created_at=assistant_task.created_at,
                completed_at=assistant_task.completed_at
            )
        )
    
    # Return the response in ACP format
    return Run(
        agent_name=agent_id,  # Return agent_id in agent_name field
        run_id=run_id,  # Using the assistant task ID as the run_id
        status=acp_status,
        output=output,
        created_at=user_task.created_at,  # Use the user task creation time as the start of the run
        finished_at=assistant_task.completed_at,
        error={"code": "failed", "message": assistant_task.metadata.get("error", "")} if acp_status == "failed" else None
    )

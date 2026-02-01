from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime

from app.models.agent import Agent
from app.models.workzone import (
    Workzone, WorkzoneInvocation, WorkzoneCreate, WorkzoneUpdate,
    WorkzoneResponse, WorkzoneList, InvocationCreate, InvocationResponse,
    InvocationListItem, InvocationList
)

router = APIRouter()

# Workzone endpoints
@router.post("/workzones", response_model=WorkzoneResponse, status_code=201)
async def create_workzone(workzone_data: WorkzoneCreate):
    """Create a new workzone for an organization"""
    workzone = Workzone(
        org_id=workzone_data.org_id,
        name=workzone_data.name,
        description=workzone_data.description,
        metadata=workzone_data.metadata or {}
    )
    await workzone.save()

    return WorkzoneResponse(
        id=str(workzone.id),
        org_id=workzone.org_id,
        name=workzone.name,
        description=workzone.description,
        metadata=workzone.metadata,
        created_at=workzone.created_at,
        updated_at=workzone.updated_at
    )


@router.get("/workzones", response_model=WorkzoneList)
async def list_workzones(
    org_id: str,
    limit: int = 10,
    skip: int = 0
):
    """List workzones for an organization"""
    # Get workzones with pagination
    workzones = await Workzone.find({"org_id": org_id}).sort([("created_at", -1)]).skip(skip).limit(limit + 1).to_list()

    has_more = len(workzones) > limit
    if has_more:
        workzones = workzones[:limit]

    workzone_responses = [
        WorkzoneResponse(
            id=str(workzone.id),
            org_id=workzone.org_id,
            name=workzone.name,
            description=workzone.description,
            metadata=workzone.metadata,
            created_at=workzone.created_at,
            updated_at=workzone.updated_at
        ) for workzone in workzones
    ]

    return WorkzoneList(workzones=workzone_responses, has_more=has_more)


@router.get("/workzones/{workzone_id}", response_model=WorkzoneResponse)
async def get_workzone(workzone_id: str, org_id: str):
    """Get a workzone by ID"""
    workzone = await Workzone.get(workzone_id)
    if not workzone:
        raise HTTPException(status_code=404, detail="Workzone not found")

    if workzone.org_id != org_id:
        raise HTTPException(status_code=403, detail="Workzone does not belong to the specified organization")

    return WorkzoneResponse(
        id=str(workzone.id),
        org_id=workzone.org_id,
        name=workzone.name,
        description=workzone.description,
        metadata=workzone.metadata,
        created_at=workzone.created_at,
        updated_at=workzone.updated_at
    )


@router.patch("/workzones/{workzone_id}", response_model=WorkzoneResponse)
async def update_workzone(workzone_id: str, org_id: str, workzone_data: WorkzoneUpdate):
    """Update a workzone"""
    workzone = await Workzone.get(workzone_id)
    if not workzone:
        raise HTTPException(status_code=404, detail="Workzone not found")

    if workzone.org_id != org_id:
        raise HTTPException(status_code=403, detail="Workzone does not belong to the specified organization")

    # Update only provided fields
    update_data = {k: v for k, v in workzone_data.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await workzone.update({"$set": update_data})

        # Refresh workzone from database
        workzone = await Workzone.get(workzone_id)

    return WorkzoneResponse(
        id=str(workzone.id),
        org_id=workzone.org_id,
        name=workzone.name,
        description=workzone.description,
        metadata=workzone.metadata,
        created_at=workzone.created_at,
        updated_at=workzone.updated_at
    )


@router.delete("/workzones/{workzone_id}", response_model=Dict[str, str])
async def delete_workzone(workzone_id: str, org_id: str):
    """Delete a workzone"""
    workzone = await Workzone.get(workzone_id)
    if not workzone:
        raise HTTPException(status_code=404, detail="Workzone not found")

    if workzone.org_id != org_id:
        raise HTTPException(status_code=403, detail="Workzone does not belong to the specified organization")

    # Delete all invocations associated with the workzone
    await WorkzoneInvocation.find({"workzone_id": workzone_id}).delete()

    # Delete the workzone
    await workzone.delete()

    return {"message": "Workzone deleted successfully"}


# Workzone Invocation endpoints
@router.post("/workzones/{workzone_id}/invocations", response_model=InvocationResponse, status_code=201)
async def create_workzone_invocation(
    workzone_id: str,
    invocation_data: InvocationCreate,
    background_tasks: BackgroundTasks
):
    """Create a new workzone invocation"""
    # Get org_id, project_id and agent_id from request body
    org_id = invocation_data.org_id
    project_id = invocation_data.project_id
    agent_id = invocation_data.agent_id

    # Verify workzone exists and belongs to organization
    workzone = await Workzone.get(workzone_id)
    if not workzone:
        raise HTTPException(status_code=404, detail="Workzone not found")

    if workzone.org_id != org_id:
        raise HTTPException(status_code=403, detail="Workzone does not belong to the specified organization")

    # Create task using existing task creation logic
    from app.api.routes.tasks import create_task
    from app.models.tasks import TaskCreate

    # Create task data with workzone metadata
    task_metadata = invocation_data.metadata or {}
    task_metadata.update({
        "workzone_id": workzone_id,
        "workzone_name": workzone.name,
        "redis_publishing_enabled": True
    })

    task_data = TaskCreate(
        content=invocation_data.content,
        metadata=task_metadata
    )

    # Call existing task creation endpoint
    task_response = await create_task(
        project_id=project_id,
        agent_id=agent_id,
        task_data=task_data,
        background_tasks=background_tasks
    )

    # Create invocation record with project_id, agent_id, and user_id
    invocation = WorkzoneInvocation(
        workzone_id=workzone_id,
        project_id=project_id,
        agent_id=agent_id,
        user_id=invocation_data.user_id,
        user_task_id=task_response.id,
        assistant_task_id=task_response.related_task_id
    )
    await invocation.save()

    return InvocationResponse(
        invocation_id=str(invocation.id),
        user_task_id=task_response.id,
        assistant_task_id=task_response.related_task_id
    )


@router.get("/workzones/{workzone_id}/invocations", response_model=InvocationList)
async def list_workzone_invocations(
    workzone_id: str,
    org_id: str,
    limit: int = 10,
    skip: int = 0,
    sort_order: str = "desc",
    user_id: Optional[str] = None
):
    """List invocations for a workzone, optionally filtered by user_id"""
    # Verify workzone exists
    workzone = await Workzone.get(workzone_id)
    if not workzone:
        raise HTTPException(status_code=404, detail="Workzone not found")

    if workzone.org_id != org_id:
        raise HTTPException(status_code=403, detail="Workzone does not belong to the specified organization")

    # Get invocations with pagination
    sort_direction = -1 if sort_order == "desc" else 1
    filter_dict = {"workzone_id": workzone_id}
    if user_id:
        filter_dict["user_id"] = user_id
    invocations = await WorkzoneInvocation.find(
        filter_dict
    ).sort([("created_at", sort_direction)]).skip(skip).limit(limit + 1).to_list()

    has_more = len(invocations) > limit
    if has_more:
        invocations = invocations[:limit]

    invocation_responses = [
        InvocationListItem(
            invocation_id=str(invocation.id),
            user_task_id=invocation.user_task_id,
            assistant_task_id=invocation.assistant_task_id,
            org_id=workzone.org_id,
            project_id=invocation.project_id,
            agent_id=invocation.agent_id,
            user_id=invocation.user_id,
            created_at=invocation.created_at
        ) for invocation in invocations
    ]

    return InvocationList(invocations=invocation_responses, has_more=has_more)


@router.get("/workzones/{workzone_id}/invocations/{invocation_id}", response_model=InvocationResponse)
async def get_workzone_invocation(workzone_id: str, invocation_id: str, org_id: str):
    """Get a workzone invocation by ID"""
    # Verify workzone exists
    workzone = await Workzone.get(workzone_id)
    if not workzone:
        raise HTTPException(status_code=404, detail="Workzone not found")

    if workzone.org_id != org_id:
        raise HTTPException(status_code=403, detail="Workzone does not belong to the specified organization")

    # Get invocation and verify it belongs to the workzone
    invocation = await WorkzoneInvocation.get(invocation_id)
    if not invocation or invocation.workzone_id != workzone_id:
        raise HTTPException(status_code=404, detail="Invocation not found")

    return InvocationResponse(
        invocation_id=invocation_id,
        user_task_id=invocation.user_task_id,
        assistant_task_id=invocation.assistant_task_id
    )

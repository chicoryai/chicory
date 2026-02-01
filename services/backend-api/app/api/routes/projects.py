from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List
from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectList
from app.utils.project_cleanup import cascade_delete_project_resources
from datetime import datetime

router = APIRouter()

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    # Check if a project with the same name already exists in this organization
    existing_project = await Project.find_one({
        "organization_id": project.organization_id,
        "name": project.name
    })

    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A project with name '{project.name}' already exists in this organization"
        )

    # Create new project document
    new_project = Project(
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        members=project.members
    )
    
    try:
        # Save to database
        await new_project.insert()
    except Exception as e:
        # Handle any database errors, including duplicate key errors
        error_msg = str(e)
        if "duplicate key error" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A project with name '{project.name}' already exists in this organization"
            )
        else:
            # Re-raise other database errors
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {error_msg}"
            )
    
    # Format the response
    return ProjectResponse(
        id=new_project.id,
        organization_id=new_project.organization_id,
        name=new_project.name,
        description=new_project.description,
        api_key=getattr(new_project, 'api_key', None),
        members=new_project.members,
        created_at=new_project.created_at.isoformat(),
        updated_at=new_project.updated_at.isoformat()
    )

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a project by ID"""
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        api_key=getattr(project, 'api_key', None),
        members=project.members,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_update: ProjectUpdate):
    """Update a project"""
    # Find the project
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    # Update fields if provided
    update_data = project_update.dict(exclude_unset=True)
    if update_data:
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()

        # Update the project
        await project.update({"$set": update_data})

        # Re-fetch the project to get updated data
        project = await Project.get(project_id)

    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        api_key=getattr(project, 'api_key', None),
        members=project.members,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )

@router.get("/projects", response_model=ProjectList)
async def list_projects(organization_id: str):
    """List all projects, optionally filtered by organization_id"""
    # Build query filter with required organization_id
    query_filter = {"organization_id": organization_id}
    
    # Find all projects matching the filter
    projects = await Project.find(query_filter).to_list()
    
    # Format the response
    project_responses = [
        ProjectResponse(
            id=proj.id,
            organization_id=proj.organization_id,
            name=proj.name,
            description=proj.description,
            api_key=getattr(proj, 'api_key', None),
            members=proj.members,
            created_at=proj.created_at.isoformat(),
            updated_at=proj.updated_at.isoformat()
        ) for proj in projects
    ]

    return ProjectList(projects=project_responses)

@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str, 
    organization_id: str,
    background_tasks: BackgroundTasks
):
    """Delete a project and all associated resources.
    
    This endpoint deletes the project document immediately and queues a background
    task to cascade delete all associated resources including:
    - S3 objects (audit trails, uploaded files)
    - Agents and their tools
    - Tasks
    - Playgrounds and invocations
    - MCP Gateways and tools
    - Evaluations and runs
    - Training jobs
    - Data sources
    - Workzone invocations
    """
    # First find the project
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Verify the project belongs to the specified organization
    if project.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Project with ID {project_id} does not belong to organization {organization_id}"
        )
    
    # Delete the project document first
    await project.delete()
    
    # Queue background task to cascade delete all associated resources
    background_tasks.add_task(cascade_delete_project_resources, project_id)
    
    return None

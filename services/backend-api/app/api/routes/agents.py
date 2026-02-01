from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime

from app.models.agent import (
    Agent, AgentCreate, AgentUpdate, AgentResponse, AgentList,
    AgentVersion, VersionHistoryResponse
)
from app.models.tasks import Task 
from app.models.tool import Tool
from app.models.mcp_gateway import MCPTool, ToolInvocation
from app.models.playground import (
    Playground, PlaygroundInvocation, PlaygroundCreate, PlaygroundUpdate,
    PlaygroundResponse, PlaygroundList, InvocationCreate, InvocationResponse,
    InvocationListItem, InvocationList
)
from app.models.workzone import Workzone, WorkzoneInvocation
from app.models.env_variable import (
    EnvVariable, EnvVariableCreate, EnvVariableUpdate, 
    EnvVariableResponse, EnvVariableList
)

router = APIRouter()

# agent endpoints
@router.post("/projects/{project_id}/agents", response_model=AgentResponse, status_code=201)
async def create_agent(project_id: str, agent_data: AgentCreate):
    """Create a new agent for a project"""
    agent = Agent(
        project_id=project_id,
        name=agent_data.name,
        description=agent_data.description,
        owner=agent_data.owner,
        instructions=agent_data.instructions,
        output_format=agent_data.output_format or "",
        state=agent_data.state or "enabled",
        deployed=agent_data.deployed or False,
        api_key=agent_data.api_key,
        capabilities=agent_data.capabilities or [],
        metadata=agent_data.metadata or {}
    )
    
    # Add initial version if instructions or output_format are provided
    if agent_data.instructions or agent_data.output_format:
        agent._add_version(
            instructions=agent_data.instructions or "",
            output_format=agent_data.output_format or "",
            updated_by=agent_data.owner
        )
    
    await agent.save()
    
    # Convert agent document to agentResponse object explicitly to handle _id aliasing
    return AgentResponse(
        id=str(agent.id),
        project_id=agent.project_id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        task_count=agent.task_count,
        instructions=agent.instructions,
        output_format=agent.output_format,
        state=agent.state,
        deployed=agent.deployed,
        api_key=agent.api_key,
        capabilities=agent.capabilities,
        metadata=agent.metadata,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )

@router.get("/projects/{project_id}/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(project_id: str, agent_id: str):
    """Get a agent by ID"""
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Convert agent document to agentResponse object explicitly to handle _id aliasing
    return AgentResponse(
        id=str(agent.id),
        project_id=agent.project_id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        task_count=agent.task_count,
        instructions=agent.instructions,
        output_format=agent.output_format,
        state=agent.state,
        deployed=agent.deployed,
        api_key=agent.api_key,
        capabilities=agent.capabilities,
        metadata=agent.metadata,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )

@router.put("/projects/{project_id}/agents/{agent_id}", response_model=AgentResponse)
async def put_agent(project_id: str, agent_id: str, agent_data: AgentCreate):
    """Replace an entire agent with new data"""
    # First check if the agent exists
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Update with all fields from agent_data
    # Preserve the original created_at but update updated_at
    created_at = agent.created_at
    task_count = agent.task_count  # Preserve task count
    
    # Replace the agent with new data
    update_data = {
        "name": agent_data.name,
        "description": agent_data.description,
        "owner": agent_data.owner,
        "instructions": agent_data.instructions,
        "output_format": agent_data.output_format,
        "state": agent_data.state or "disabled",
        "deployed": agent_data.deployed or False,
        "api_key": agent_data.api_key,
        "capabilities": agent_data.capabilities or [],
        "metadata": agent_data.metadata or {},
        "updated_at": datetime.utcnow()
    }
    
    await agent.update({"$set": update_data})
    
    # Refresh agent from the database to get the updated values
    agent = await Agent.get(agent_id)
    
    # Convert agent document to AgentResponse object
    return AgentResponse(
        id=str(agent.id),
        project_id=agent.project_id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        task_count=agent.task_count,
        instructions=agent.instructions,
        output_format=agent.output_format,
        state=agent.state,
        deployed=agent.deployed,
        api_key=agent.api_key,
        capabilities=agent.capabilities,
        metadata=agent.metadata,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )

@router.get("/projects/{project_id}/agents", response_model=AgentList)
async def list_agents(project_id: str, owner: Optional[str] = None):
    """
    List all agents for a project with optional filtering
    
    Parameters:
    - project_id: The ID of the project to list agents for
    - owner: Optional owner to filter agents by
    """
    try:
        print(f"Searching for agents with project_id: {project_id}, owner filter: {owner}")
        
        # Build the query with project_id and optional owner filter
        query = {"project_id": project_id}
        if owner is not None:
            query["owner"] = owner
            
        # Use a raw query to avoid validation errors from documents with missing fields
        raw_agents = await Agent.get_motor_collection().find(query).to_list(length=None)
        print(f"Found {len(raw_agents)} raw agent documents")
        
        # Convert raw documents to agentResponse objects with proper field handling
        agent_responses = []
        for raw_agent in raw_agents:
            try:
                # Set default values for any missing fields
                agent_response = AgentResponse(
                    id=str(raw_agent.get("_id", "unknown")),
                    project_id=raw_agent.get("project_id", project_id),
                    # Add a default name for agents that are missing it
                    name=raw_agent.get("name", "Untitled agent"),
                    description=raw_agent.get("description"),
                    owner=raw_agent.get("owner"),
                    task_count=raw_agent.get("task_count", 0),
                    instructions=raw_agent.get("instructions"),
                    output_format=raw_agent.get("output_format"),
                    state=raw_agent.get("state", "enabled"),
                    deployed=raw_agent.get("deployed", False),
                    api_key=raw_agent.get("api_key"),
                    capabilities=raw_agent.get("capabilities", []),
                    metadata=raw_agent.get("metadata", {}),
                    created_at=raw_agent.get("created_at", datetime.utcnow()),
                    updated_at=raw_agent.get("updated_at", datetime.utcnow())
                )
                agent_responses.append(agent_response)
            except Exception as e:
                # Log the error but continue processing other agents
                print(f"Error processing agent document: {e}")
        
        # Return explicit empty list if no agents were found
        result = AgentList(agents=agent_responses)
        print(f"Returning agentList with {len(agent_responses)} items")
        return result
    except Exception as e:
        print(f"Unexpected error in list_agents: {e}")
        # Return empty list instead of throwing an error
        return AgentList(agents=[])

@router.patch("/projects/{project_id}/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    project_id: str, 
    agent_id: str, 
    agent_data: AgentUpdate
):
    """Update agent information"""
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Extract updated_by from the request body before building update_data
    updated_by = agent_data.updated_by
    
    # Update only the fields that are provided (exclude updated_by from the DB update)
    update_data = agent_data.dict(exclude_unset=True, exclude={'updated_by'})
    update_data = {k: v for k, v in update_data.items() if v is not None}
    if update_data:
        # Check if instructions or output_format are being updated
        instructions_changed = "instructions" in update_data and update_data["instructions"] != agent.instructions
        output_format_changed = "output_format" in update_data and update_data["output_format"] != agent.output_format
        
        # Create version entry when instructions or output_format changed
        # This saves the NEW state to version history
        if instructions_changed or output_format_changed:
            # Use updated_by from request if provided, otherwise fallback to agent.owner
            version_updater = updated_by or agent.owner
            
            # Get the new values (use existing if not being updated)
            new_instructions = update_data.get("instructions", agent.instructions)
            new_output_format = update_data.get("output_format", agent.output_format)
            
            # Add the NEW state to version history
            agent._add_version(
                instructions=new_instructions,
                output_format=new_output_format,
                updated_by=version_updater
            )
            # Add versions to update_data to persist it
            update_data["versions"] = agent.versions
        
        agent.updated_at = datetime.utcnow()
        await agent.update({"$set": {**update_data, "updated_at": agent.updated_at}})
        
        # Refresh agent from the database to get the updated values
        agent = await agent.get(agent_id)
    
    # Convert agent document to agentResponse object explicitly to handle _id aliasing
    return AgentResponse(
        id=str(agent.id),
        project_id=agent.project_id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        task_count=agent.task_count,
        instructions=agent.instructions,
        output_format=agent.output_format,
        state=agent.state,
        deployed=agent.deployed,
        api_key=agent.api_key,
        capabilities=agent.capabilities,
        metadata=agent.metadata,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )

@router.delete("/projects/{project_id}/agents/{agent_id}", response_model=Dict[str, str])
async def delete_agent(project_id: str, agent_id: str):
    """Delete a agent"""
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="agent does not belong to the specified project")
    
    # Delete all tasks associated with the agent
    await Task.find({"agent_id": agent_id}).delete()
    
    # Delete all tools associated with the agent
    await Tool.find({"agent_id": agent_id}).delete()
    
    # Delete all MCP tools associated with the agent and their invocations
    mcp_tools = await MCPTool.find({"agent_id": agent_id}).to_list()
    for mcp_tool in mcp_tools:
        # Delete all invocations for this MCP tool
        await ToolInvocation.find({"tool_id": str(mcp_tool.id)}).delete()
    # Delete the MCP tools themselves
    await MCPTool.find({"agent_id": agent_id}).delete()
    
    # Delete all playgrounds associated with the agent and their invocations
    playgrounds = await Playground.find({"agent_id": agent_id}).to_list()
    for playground in playgrounds:
        # Delete all invocations for this playground
        await PlaygroundInvocation.find({"playground_id": str(playground.id)}).delete()
    # Delete the playgrounds themselves
    await Playground.find({"agent_id": agent_id}).delete()

    # Delete all workzone invocations that reference this agent
    # Note: Workzones are org-level resources and are not deleted when an agent is deleted
    await WorkzoneInvocation.find({"agent_id": agent_id}).delete()

    # Delete all environment variables associated with the agent
    await EnvVariable.find({"agent_id": agent_id}).delete()

    # Delete the agent
    await agent.delete()
    
    return {"message": "agent deleted successfully"}


# Playground endpoints
@router.post("/projects/{project_id}/agents/{agent_id}/playgrounds", response_model=PlaygroundResponse, status_code=201)
async def create_playground(project_id: str, agent_id: str, playground_data: PlaygroundCreate):
    """Create a new playground for an agent"""
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    playground = Playground(
        agent_id=agent_id,
        project_id=project_id,
        name=playground_data.name,
        description=playground_data.description,
        metadata=playground_data.metadata or {}
    )
    await playground.save()
    
    return PlaygroundResponse(
        id=str(playground.id),
        agent_id=playground.agent_id,
        project_id=playground.project_id,
        name=playground.name,
        description=playground.description,
        metadata=playground.metadata,
        created_at=playground.created_at,
        updated_at=playground.updated_at
    )


@router.get("/projects/{project_id}/agents/{agent_id}/playgrounds", response_model=PlaygroundList)
async def list_playgrounds(
    project_id: str, 
    agent_id: str,
    limit: int = 10,
    skip: int = 0
):
    """List playgrounds for an agent"""
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Get playgrounds with pagination
    playgrounds = await Playground.find(
        {"agent_id": agent_id, "project_id": project_id}
    ).sort([("created_at", -1)]).skip(skip).limit(limit + 1).to_list()
    
    has_more = len(playgrounds) > limit
    if has_more:
        playgrounds = playgrounds[:limit]
    
    playground_responses = [
        PlaygroundResponse(
            id=str(playground.id),
            agent_id=playground.agent_id,
            project_id=playground.project_id,
            name=playground.name,
            description=playground.description,
            metadata=playground.metadata,
            created_at=playground.created_at,
            updated_at=playground.updated_at
        ) for playground in playgrounds
    ]
    
    return PlaygroundList(playgrounds=playground_responses, has_more=has_more)


@router.get("/projects/{project_id}/agents/{agent_id}/playgrounds/{playground_id}", response_model=PlaygroundResponse)
async def get_playground(project_id: str, agent_id: str, playground_id: str):
    """Get a playground by ID"""
    playground = await Playground.get(playground_id)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
        
    if playground.project_id != project_id or playground.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Playground does not belong to the specified project/agent")
    
    return PlaygroundResponse(
        id=str(playground.id),
        agent_id=playground.agent_id,
        project_id=playground.project_id,
        name=playground.name,
        description=playground.description,
        metadata=playground.metadata,
        created_at=playground.created_at,
        updated_at=playground.updated_at
    )


@router.patch("/projects/{project_id}/agents/{agent_id}/playgrounds/{playground_id}", response_model=PlaygroundResponse)
async def update_playground(project_id: str, agent_id: str, playground_id: str, playground_data: PlaygroundUpdate):
    """Update a playground"""
    playground = await Playground.get(playground_id)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
        
    if playground.project_id != project_id or playground.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Playground does not belong to the specified project/agent")
    
    # Update only provided fields
    update_data = {k: v for k, v in playground_data.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await playground.update({"$set": update_data})
        
        # Refresh playground from database
        playground = await Playground.get(playground_id)
    
    return PlaygroundResponse(
        id=str(playground.id),
        agent_id=playground.agent_id,
        project_id=playground.project_id,
        name=playground.name,
        description=playground.description,
        metadata=playground.metadata,
        created_at=playground.created_at,
        updated_at=playground.updated_at
    )


@router.delete("/projects/{project_id}/agents/{agent_id}/playgrounds/{playground_id}", response_model=Dict[str, str])
async def delete_playground(project_id: str, agent_id: str, playground_id: str):
    """Delete a playground"""
    playground = await Playground.get(playground_id)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
        
    if playground.project_id != project_id or playground.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Playground does not belong to the specified project/agent")
    
    # Delete all invocations associated with the playground
    await PlaygroundInvocation.find({"playground_id": playground_id}).delete()
    
    # Delete the playground
    await playground.delete()
    
    return {"message": "Playground deleted successfully"}


# Playground Invocation endpoints
@router.post("/projects/{project_id}/agents/{agent_id}/playgrounds/{playground_id}/invocations", response_model=InvocationResponse, status_code=201)
async def create_playground_invocation(
    project_id: str, 
    agent_id: str, 
    playground_id: str, 
    invocation_data: InvocationCreate,
    background_tasks: BackgroundTasks
):
    """Create a new playground invocation"""
    # Verify playground exists and belongs to project/agent
    playground = await Playground.get(playground_id)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
        
    if playground.project_id != project_id or playground.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Playground does not belong to the specified project/agent")
    
    # Create task using existing task creation logic
    from app.api.routes.tasks import create_task
    from app.models.tasks import TaskCreate
    
    # Create task data with playground metadata
    task_metadata = invocation_data.metadata or {}
    task_metadata.update({
        "playground_id": playground_id,
        "playground_name": playground.name,
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
    
    # Create invocation record
    invocation = PlaygroundInvocation(
        playground_id=playground_id,
        user_task_id=task_response.id,
        assistant_task_id=task_response.related_task_id
    )
    await invocation.save()
    
    return InvocationResponse(
        invocation_id=str(invocation.id),
        user_task_id=task_response.id,
        assistant_task_id=task_response.related_task_id
    )


@router.get("/projects/{project_id}/agents/{agent_id}/playgrounds/{playground_id}/invocations", response_model=InvocationList)
async def list_playground_invocations(
    project_id: str,
    agent_id: str,
    playground_id: str,
    limit: int = 10,
    skip: int = 0,
    sort_order: str = "desc"
):
    """List invocations for a playground"""
    # Verify playground exists and belongs to project/agent
    playground = await Playground.get(playground_id)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
        
    if playground.project_id != project_id or playground.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Playground does not belong to the specified project/agent")
    
    # Get invocations with pagination
    sort_direction = -1 if sort_order == "desc" else 1
    invocations = await PlaygroundInvocation.find(
        {"playground_id": playground_id}
    ).sort([("created_at", sort_direction)]).skip(skip).limit(limit + 1).to_list()
    
    has_more = len(invocations) > limit
    if has_more:
        invocations = invocations[:limit]
    
    invocation_responses = [
        InvocationListItem(
            invocation_id=str(invocation.id),
            user_task_id=invocation.user_task_id,
            assistant_task_id=invocation.assistant_task_id,
            created_at=invocation.created_at
        ) for invocation in invocations
    ]
    
    return InvocationList(invocations=invocation_responses, has_more=has_more)


@router.get("/projects/{project_id}/agents/{agent_id}/playgrounds/{playground_id}/invocations/{invocation_id}", response_model=InvocationResponse)
async def get_playground_invocation(project_id: str, agent_id: str, playground_id: str, invocation_id: str):
    """Get a playground invocation by ID"""
    # Verify playground exists and belongs to project/agent
    playground = await Playground.get(playground_id)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
        
    if playground.project_id != project_id or playground.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Playground does not belong to the specified project/agent")
    
    # Get invocation and verify it belongs to the playground
    invocation = await PlaygroundInvocation.get(invocation_id)
    if not invocation or invocation.playground_id != playground_id:
        raise HTTPException(status_code=404, detail="Invocation not found")
    
    return InvocationResponse(
        invocation_id=invocation_id,
        user_task_id=invocation.user_task_id,
        assistant_task_id=invocation.assistant_task_id
    )


# Version History Endpoints
@router.get("/projects/{project_id}/agents/{agent_id}/versions", response_model=VersionHistoryResponse)
async def get_agent_versions(project_id: str, agent_id: str):
    """Get version history for an agent, including current version as the first item"""
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Convert version dicts to AgentVersion objects
    # agent.versions contains snapshots created when instructions/output_format are updated
    # The first entry (index 0) is the most recent update, subsequent entries are older versions
    # Note: For newly created agents, the initial version is added during creation
    versions = []
    for v in agent.versions:
        versions.append(AgentVersion(
            instructions=v.get("instructions"),
            output_format=v.get("output_format"),
            created_at=v.get("created_at", datetime.utcnow()),
            updated_by=v.get("updated_by")
        ))
    
    return VersionHistoryResponse(
        versions=versions,
        total_count=len(versions)
    )


@router.get("/projects/{project_id}/agents/{agent_id}/versions/{version_index}", response_model=AgentVersion)
async def get_agent_version(project_id: str, agent_id: str, version_index: int):
    """Get a specific version by index (0 = most recent, 1 = second most recent, etc.)"""
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Validate version index
    if version_index < 0 or version_index >= len(agent.versions):
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Return the version at the specified index
    v = agent.versions[version_index]
    return AgentVersion(
        instructions=v.get("instructions"),
        output_format=v.get("output_format"),
        created_at=v.get("created_at", datetime.utcnow()),
        updated_by=v.get("updated_by")
    )


# Environment Variable Endpoints
@router.post("/projects/{project_id}/agents/{agent_id}/env-variables", response_model=EnvVariableResponse, status_code=201)
async def create_env_variable(project_id: str, agent_id: str, env_var_data: EnvVariableCreate):
    """Add a new environment variable to an agent"""
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Check if env variable with same key already exists for this agent
    existing = await EnvVariable.find_one({"agent_id": agent_id, "key": env_var_data.key})
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Environment variable with key '{env_var_data.key}' already exists for this agent"
        )
    
    # Create the environment variable
    env_var = EnvVariable(
        agent_id=agent_id,
        key=env_var_data.key,
        value=env_var_data.value,
        description=env_var_data.description
    )
    await env_var.save()
    
    return EnvVariableResponse(
        id=str(env_var.id),
        agent_id=env_var.agent_id,
        key=env_var.key,
        value=env_var.value,
        description=env_var.description,
        created_at=env_var.created_at,
        updated_at=env_var.updated_at
    )


@router.get("/projects/{project_id}/agents/{agent_id}/env-variables", response_model=EnvVariableList)
async def list_env_variables(project_id: str, agent_id: str):
    """List all environment variables for an agent"""
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Get all env variables for this agent
    env_vars = await EnvVariable.find({"agent_id": agent_id}).to_list()
    
    env_var_responses = [
        EnvVariableResponse(
            id=str(env_var.id),
            agent_id=env_var.agent_id,
            key=env_var.key,
            value=env_var.value,
            description=env_var.description,
            created_at=env_var.created_at,
            updated_at=env_var.updated_at
        ) for env_var in env_vars
    ]
    
    return EnvVariableList(env_variables=env_var_responses)


@router.get("/projects/{project_id}/agents/{agent_id}/env-variables/{env_var_id}", response_model=EnvVariableResponse)
async def get_env_variable(project_id: str, agent_id: str, env_var_id: str):
    """Get a specific environment variable by ID"""
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Get the env variable
    env_var = await EnvVariable.get(env_var_id)
    if not env_var or env_var.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    return EnvVariableResponse(
        id=str(env_var.id),
        agent_id=env_var.agent_id,
        key=env_var.key,
        value=env_var.value,
        description=env_var.description,
        created_at=env_var.created_at,
        updated_at=env_var.updated_at
    )


@router.patch("/projects/{project_id}/agents/{agent_id}/env-variables/{env_var_id}", response_model=EnvVariableResponse)
async def update_env_variable(project_id: str, agent_id: str, env_var_id: str, env_var_data: EnvVariableUpdate):
    """Update an environment variable"""
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Get the env variable
    env_var = await EnvVariable.get(env_var_id)
    if not env_var or env_var.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    # If key is being updated, check for duplicates
    if env_var_data.key and env_var_data.key != env_var.key:
        existing = await EnvVariable.find_one({"agent_id": agent_id, "key": env_var_data.key})
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Environment variable with key '{env_var_data.key}' already exists for this agent"
            )
    
    # Update only provided fields
    update_data = {k: v for k, v in env_var_data.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await env_var.update({"$set": update_data})
        
        # Refresh from database
        env_var = await EnvVariable.get(env_var_id)
    
    return EnvVariableResponse(
        id=str(env_var.id),
        agent_id=env_var.agent_id,
        key=env_var.key,
        value=env_var.value,
        description=env_var.description,
        created_at=env_var.created_at,
        updated_at=env_var.updated_at
    )


@router.delete("/projects/{project_id}/agents/{agent_id}/env-variables/{env_var_id}", status_code=204)
async def delete_env_variable(project_id: str, agent_id: str, env_var_id: str):
    """Delete an environment variable"""
    # Verify agent exists and belongs to project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Get the env variable
    env_var = await EnvVariable.get(env_var_id)
    if not env_var or env_var.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    # Delete the env variable
    await env_var.delete()
    return None

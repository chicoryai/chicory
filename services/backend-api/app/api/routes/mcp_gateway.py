from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from datetime import datetime
import secrets
import string
import uuid

from app.models.mcp_gateway import (
    MCPGateway, MCPGatewayCreate, MCPGatewayUpdate, MCPGatewayResponse, MCPGatewayList,
    MCPTool, MCPToolCreate, MCPToolUpdate, MCPToolResponse, MCPToolList, MCPToolStatus,
    ToolInvocation, CreateInvocationRequest, InvocationResponse
)
from app.utils.tool_metadata_orchestration import start_tool_metadata_generation

router = APIRouter()

async def _remove_tool_metadata_from_agent(agent_id: str, gateway_id: str, tool_id: str):
    """Remove MCP tool metadata from agent when tool is deleted"""
    try:
        from app.models.agent import Agent
        
        # Get the agent
        agent = await Agent.get(agent_id)
        if not agent:
            print(f"Agent {agent_id} not found when trying to remove tool metadata")
            return
        
        # Get current metadata
        current_metadata = agent.metadata or {}
        mcp_gateways = current_metadata.get("mcp_gateways", [])
        
        # Remove the specific gateway/tool entry
        updated_gateways = [
            entry for entry in mcp_gateways 
            if not (entry.get("gateway_id") == gateway_id and entry.get("tool_id") == tool_id)
        ]
        
        # Update the metadata
        current_metadata["mcp_gateways"] = updated_gateways
        
        # Update the agent document
        await agent.update({
            "$set": {
                "metadata": current_metadata,
                "updated_at": datetime.utcnow()
            }
        })
        
        print(f"Successfully removed MCP tool {tool_id} metadata from agent {agent_id}")
        
    except Exception as e:
        print(f"Error removing tool metadata from agent {agent_id}: {e}")
        # Don't fail the tool deletion if metadata cleanup fails

@router.post("/projects/{project_id}/mcp-gateway", response_model=MCPGatewayResponse, status_code=201)
async def create_gateway(project_id: str, gateway_data: MCPGatewayCreate):
    """Create a new MCP gateway for a project"""
    gateway = MCPGateway(
        project_id=project_id,
        name=gateway_data.name,
        description=gateway_data.description,
        api_key=gateway_data.api_key
    )
    await gateway.save()
    
    # Convert gateway document to MCPGatewayResponse object explicitly to handle _id aliasing
    return MCPGatewayResponse(
        id=str(gateway.id),
        project_id=gateway.project_id,
        name=gateway.name,
        description=gateway.description,
        api_key=gateway.api_key,
        enabled=gateway.enabled,
        created_at=gateway.created_at,
        updated_at=gateway.updated_at
    )


@router.get("/projects/{project_id}/mcp-gateway/{gateway_id}", response_model=MCPGatewayResponse)
async def get_gateway(project_id: str, gateway_id: str):
    """Get a gateway by ID"""
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    # Convert gateway document to MCPGatewayResponse object explicitly to handle _id aliasing
    return MCPGatewayResponse(
        id=str(gateway.id),
        project_id=gateway.project_id,
        name=gateway.name,
        description=gateway.description,
        api_key=gateway.api_key,
        enabled=gateway.enabled,
        created_at=gateway.created_at,
        updated_at=gateway.updated_at
    )


@router.get("/projects/{project_id}/mcp-gateway", response_model=MCPGatewayList)
async def list_gateways(project_id: str):
    """
    List all MCP gateways for a project
    
    Parameters:
    - project_id: The ID of the project to list gateways for
    """
    try:
        print(f"Searching for gateways with project_id: {project_id}")
        
        # Use a raw query to avoid validation errors from documents with missing fields
        raw_gateways = await MCPGateway.get_motor_collection().find({"project_id": project_id}).to_list(length=None)
        print(f"Found {len(raw_gateways)} raw gateway documents")
        
        # Convert raw documents to MCPGatewayResponse objects with proper field handling
        gateway_responses = []
        for raw_gateway in raw_gateways:
            try:
                # Set default values for any missing fields
                gateway_response = MCPGatewayResponse(
                    id=str(raw_gateway.get("_id", "unknown")),
                    project_id=raw_gateway.get("project_id", project_id),
                    name=raw_gateway.get("name", "Untitled Gateway"),
                    description=raw_gateway.get("description"),
                    api_key=raw_gateway.get("api_key", ""),
                    enabled=raw_gateway.get("enabled", True),
                    created_at=raw_gateway.get("created_at", datetime.utcnow()),
                    updated_at=raw_gateway.get("updated_at", datetime.utcnow())
                )
                gateway_responses.append(gateway_response)
            except Exception as e:
                # Log the error but continue processing other gateways
                print(f"Error processing gateway document: {e}")
        
        # Return explicit empty list if no gateways were found
        result = MCPGatewayList(gateways=gateway_responses)
        print(f"Returning MCPGatewayList with {len(gateway_responses)} items")
        return result
    except Exception as e:
        print(f"Unexpected error in list_gateways: {e}")
        # Return empty list instead of throwing an error
        return MCPGatewayList(gateways=[])


@router.patch("/projects/{project_id}/mcp-gateway/{gateway_id}", response_model=MCPGatewayResponse)
async def update_gateway(project_id: str, gateway_id: str, gateway_data: MCPGatewayUpdate):
    """Update gateway information"""
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    # Update only the fields that are provided
    update_data = {k: v for k, v in gateway_data.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        gateway.updated_at = datetime.utcnow()
        await gateway.update({"$set": {**update_data, "updated_at": gateway.updated_at}})
        
        # Refresh gateway from the database to get the updated values
        gateway = await MCPGateway.get(gateway_id)
    
    # Convert gateway document to MCPGatewayResponse object explicitly to handle _id aliasing
    return MCPGatewayResponse(
        id=str(gateway.id),
        project_id=gateway.project_id,
        name=gateway.name,
        description=gateway.description,
        api_key=gateway.api_key,
        enabled=gateway.enabled,
        created_at=gateway.created_at,
        updated_at=gateway.updated_at
    )


@router.delete("/projects/{project_id}/mcp-gateway/{gateway_id}", response_model=Dict[str, str])
async def delete_gateway(project_id: str, gateway_id: str):
    """Delete a gateway"""
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    # Delete all tools associated with the gateway
    await MCPTool.find({"gateway_id": gateway_id}).delete()
    
    # Delete the gateway
    await gateway.delete()
    
    return {"message": "Gateway deleted successfully"}


# Tool endpoints
@router.post("/projects/{project_id}/mcp-gateway/{gateway_id}/tools", response_model=MCPToolResponse, status_code=201)
async def create_tool(project_id: str, gateway_id: str, tool_data: MCPToolCreate, background_tasks: BackgroundTasks):
    """Add an agent as a tool to the gateway"""
    # Verify gateway exists and belongs to project
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    # Create tool without name - AI will generate everything
    tool = MCPTool(
        gateway_id=gateway_id,
        tool_name="",  # AI will generate tool name
        agent_id=tool_data.agent_id,
        description=None,  # AI will generate description
        status=MCPToolStatus.GENERATING
    )
    await tool.save()
    
    # Trigger AI metadata generation in background
    # Pass tool object directly to avoid read-after-write race condition
    background_tasks.add_task(start_tool_metadata_generation, tool)
    
    # Convert tool document to MCPToolResponse object explicitly to handle _id aliasing
    return MCPToolResponse(
        id=str(tool.id),
        gateway_id=tool.gateway_id,
        tool_name=tool.tool_name,
        agent_id=tool.agent_id,
        description=tool.description,
        input_schema=tool.input_schema,
        output_format=tool.output_format,
        status=tool.status.value,
        enabled=tool.enabled,
        created_at=tool.created_at,
        updated_at=tool.updated_at
    )


@router.get("/projects/{project_id}/mcp-gateway/{gateway_id}/tools/{tool_id}", response_model=MCPToolResponse)
async def get_tool(project_id: str, gateway_id: str, tool_id: str):
    """Get a tool by ID"""
    # Verify gateway exists and belongs to project
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    tool = await MCPTool.get(tool_id)
    if not tool or tool.gateway_id != gateway_id:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Convert tool document to MCPToolResponse object explicitly to handle _id aliasing
    return MCPToolResponse(
        id=str(tool.id),
        gateway_id=tool.gateway_id,
        tool_name=tool.tool_name,
        agent_id=tool.agent_id,
        description=tool.description,
        input_schema=tool.input_schema,
        output_format=tool.output_format,
        status=tool.status.value,
        enabled=tool.enabled,
        created_at=tool.created_at,
        updated_at=tool.updated_at
    )


@router.get("/projects/{project_id}/mcp-gateway/{gateway_id}/tools", response_model=MCPToolList)
async def list_tools(project_id: str, gateway_id: str):
    """
    List all tools for a gateway
    
    Parameters:
    - project_id: The ID of the project
    - gateway_id: The ID of the gateway to list tools for
    """
    # Verify gateway exists and belongs to project
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    try:
        print(f"Searching for tools with gateway_id: {gateway_id}")
        
        # Use a raw query to avoid validation errors from documents with missing fields
        raw_tools = await MCPTool.get_motor_collection().find({"gateway_id": gateway_id}).to_list(length=None)
        print(f"Found {len(raw_tools)} raw tool documents")
        
        # Convert raw documents to MCPToolResponse objects with proper field handling
        tool_responses = []
        for raw_tool in raw_tools:
            try:
                # Set default values for any missing fields
                tool_response = MCPToolResponse(
                    id=str(raw_tool.get("_id", "unknown")),
                    gateway_id=raw_tool.get("gateway_id", gateway_id),
                    tool_name=raw_tool.get("tool_name", "Untitled Tool"),
                    agent_id=raw_tool.get("agent_id", ""),
                    description=raw_tool.get("description"),
                    input_schema=raw_tool.get("input_schema"),
                    output_format=raw_tool.get("output_format"),
                    status=raw_tool.get("status", "generating"),
                    enabled=raw_tool.get("enabled", False),
                    created_at=raw_tool.get("created_at", datetime.utcnow()),
                    updated_at=raw_tool.get("updated_at", datetime.utcnow())
                )
                tool_responses.append(tool_response)
            except Exception as e:
                # Log the error but continue processing other tools
                print(f"Error processing tool document: {e}")
        
        # Return explicit empty list if no tools were found
        result = MCPToolList(tools=tool_responses)
        print(f"Returning MCPToolList with {len(tool_responses)} items")
        return result
    except Exception as e:
        print(f"Unexpected error in list_tools: {e}")
        # Return empty list instead of throwing an error
        return MCPToolList(tools=[])


@router.patch("/projects/{project_id}/mcp-gateway/{gateway_id}/tools/{tool_id}", response_model=MCPToolResponse)
async def update_tool(project_id: str, gateway_id: str, tool_id: str, tool_update: MCPToolUpdate):
    """Update tool information"""
    # Verify gateway exists and belongs to project
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    tool = await MCPTool.get(tool_id)
    if not tool or tool.gateway_id != gateway_id:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Update only the fields that are provided
    update_data = {k: v for k, v in tool_update.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        tool.updated_at = datetime.utcnow()
        await tool.update({"$set": {**update_data, "updated_at": tool.updated_at}})
        
        # Refresh tool from the database to get the updated values
        tool = await MCPTool.get(tool_id)
    
    # Convert tool document to MCPToolResponse object explicitly to handle _id aliasing
    return MCPToolResponse(
        id=str(tool.id),
        gateway_id=tool.gateway_id,
        tool_name=tool.tool_name,
        agent_id=tool.agent_id,
        description=tool.description,
        input_schema=tool.input_schema,
        output_format=tool.output_format,
        status=tool.status.value,
        enabled=tool.enabled,
        created_at=tool.created_at,
        updated_at=tool.updated_at
    )


@router.delete("/projects/{project_id}/mcp-gateway/{gateway_id}/tools/{tool_id}", response_model=Dict[str, str])
async def delete_tool(project_id: str, gateway_id: str, tool_id: str):
    """Delete a tool"""
    # Verify gateway exists and belongs to project
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    tool = await MCPTool.get(tool_id)
    if not tool or tool.gateway_id != gateway_id:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Remove tool metadata from agent before deleting the tool
    await _remove_tool_metadata_from_agent(tool.agent_id, gateway_id, tool_id)
    
    # Delete the tool
    await tool.delete()
    
    return {"message": "Tool deleted successfully"}


@router.post("/projects/{project_id}/mcp-gateway/{gateway_id}/tools/{tool_id}/invocations", response_model=InvocationResponse)
async def create_invocation(project_id: str, gateway_id: str, tool_id: str, request: CreateInvocationRequest, background_tasks: BackgroundTasks):
    """Create a new tool invocation"""
    from app.models.tasks import Task, TaskRole, TaskStatus
    from app.utils.rabbitmq_client import queue_agent_task
    from datetime import timezone
    import json
    import time
    
    # Verify gateway exists and belongs to project
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    # Validate tool exists, belongs to gateway, and is enabled
    tool = await MCPTool.get(tool_id)
    if not tool or tool.gateway_id != gateway_id:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    if not tool.enabled:
        raise HTTPException(status_code=400, detail="Tool is not enabled")
    
    if tool.status != MCPToolStatus.READY:
        raise HTTPException(status_code=400, detail=f"Tool is not ready. Current status: {tool.status}")
    
    # Validate input arguments against tool's input schema
    if tool.input_schema:
        from jsonschema import validate, ValidationError
        try:
            validate(instance=request.arguments, schema=tool.input_schema)
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Input validation failed: {e.message}"
            )
    
    # Generate invocation ID first
    invocation_id = str(uuid.uuid4())
    
    # Create task using the existing task creation endpoint
    from app.api.routes.tasks import create_task
    from app.models.tasks import TaskCreate
    
    # Create task data
    task_data = TaskCreate(
        content=json.dumps(request.arguments),
        metadata={"invocation_id": invocation_id, "tool_id": tool_id}
    )
    
    # Call the existing task creation endpoint
    task_response = await create_task(
        project_id=project_id,
        agent_id=tool.agent_id,
        task_data=task_data,
        background_tasks=background_tasks
    )
    
    # Create invocation record using task response data
    invocation = ToolInvocation(
        id=invocation_id,
        tool_id=tool_id,
        user_task_id=task_response.id,
        assistant_task_id=task_response.related_task_id
    )
    await invocation.save()
    
    # Task is already queued by create_task
    # Caller will poll using assistant_task_id
    
    return InvocationResponse(
        invocation_id=invocation_id,
        user_task_id=task_response.id,
        assistant_task_id=task_response.related_task_id
    )


@router.get("/projects/{project_id}/mcp-gateway/{gateway_id}/tools/{tool_id}/invocations/{invocation_id}", response_model=InvocationResponse)
async def get_invocation_status(project_id: str, gateway_id: str, tool_id: str, invocation_id: str):
    """Get invocation status"""
    # Verify gateway exists and belongs to project
    gateway = await MCPGateway.get(gateway_id)
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
        
    if gateway.project_id != project_id:
        raise HTTPException(status_code=400, detail="Gateway does not belong to the specified project")
    
    # Verify tool exists and belongs to gateway
    tool = await MCPTool.get(tool_id)
    if not tool or tool.gateway_id != gateway_id:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Get invocation and verify it belongs to the tool
    invocation = await ToolInvocation.get(invocation_id)
    if not invocation or invocation.tool_id != tool_id:
        raise HTTPException(status_code=404, detail="Invocation not found")
    
    return InvocationResponse(
        invocation_id=invocation_id,
        user_task_id=invocation.user_task_id,
        assistant_task_id=invocation.assistant_task_id,
        execution_time_seconds=invocation.execution_time_seconds,
        error=invocation.error
    )



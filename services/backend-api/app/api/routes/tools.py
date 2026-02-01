from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from datetime import datetime
from bson import ObjectId

# Import shared MCP tools utility
from app.utils.mcp_tools import fetch_tools_from_mcp_server

from app.models.agent import Agent
from app.models.tool import (
    Tool, ToolCreate, ToolUpdate, ToolResponse, ToolList
)

router = APIRouter()

# Tool Management Endpoints

@router.post("/projects/{project_id}/agents/{agent_id}/tools", response_model=ToolResponse, status_code=201)
async def add_tool_to_agent(project_id: str, agent_id: str, tool_data: ToolCreate):
    """Add a new tool to an agent"""
    # Check if the agent exists and belongs to the project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Create tool with the Tool model
    now = datetime.utcnow()
    
    # For MCP tool type, connect to the server and get available tools
    config = tool_data.config.copy()  # Create a copy to avoid modifying the input
    if tool_data.tool_type == "mcp" and "server_url" in config:
        try:
            # Extract MCP server configuration
            server_name = tool_data.name
            server_url = config["server_url"]
            transport = config.get("transport", "streamable_http")
            headers = config.get("headers", {})
            
            # Use the shared utility function to fetch tools
            available_tools = await fetch_tools_from_mcp_server(
                server_url=server_url,
                server_name=server_name,
                headers=headers,
                transport=transport
            )
            
            # Add available tools to the configuration
            config["available_tools"] = available_tools
            
        except Exception as e:
            # Return error with appropriate status code (Bad Request)
            error_msg = f"Failed to connect to MCP server at {server_url}: {str(e.args[len(e.args)-1])}"
            print(error_msg)  # Log the error
            raise HTTPException(status_code=400, detail=error_msg)
    
    # Create a new Tool instance
    new_tool = Tool(
        agent_id=agent_id,
        name=tool_data.name,
        tool_type=tool_data.tool_type,
        description=tool_data.description,
        provider=tool_data.provider,
        config=config,  # Use the potentially updated config
        enabled=tool_data.enabled,
        created_at=now,
        updated_at=now
    )
    
    # Save the tool to the database
    await new_tool.save()
    
    # Return the created tool
    return ToolResponse(
        id=str(new_tool.id),
        agent_id=new_tool.agent_id,
        name=new_tool.name,
        tool_type=new_tool.tool_type,
        description=new_tool.description,
        provider=new_tool.provider,
        config=new_tool.config,
        enabled=new_tool.enabled,
        created_at=new_tool.created_at,
        updated_at=new_tool.updated_at
    )


@router.get("/projects/{project_id}/agents/{agent_id}/tools", response_model=ToolList)
async def list_agent_tools(project_id: str, agent_id: str):
    """List all tools for a specific agent"""
    # Check if the agent exists and belongs to the project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Query the tools for this agent using the Tool model
    tools_query = await Tool.find({"agent_id": agent_id}).to_list()
    
    # Convert to list of ToolResponse objects
    tools = []
    for tool in tools_query:
        tools.append(ToolResponse(
            id=str(tool.id),
            agent_id=tool.agent_id,
            name=tool.name,
            tool_type=tool.tool_type,
            description=tool.description,
            provider=tool.provider,
            config=tool.config,
            enabled=tool.enabled,
            created_at=tool.created_at,
            updated_at=tool.updated_at
        ))
    
    return ToolList(tools=tools)


@router.get("/projects/{project_id}/agents/{agent_id}/tools/{tool_id}", response_model=ToolResponse)
async def get_agent_tool(project_id: str, agent_id: str, tool_id: str):
    """Get a specific tool for an agent"""
    # Check if the agent exists and belongs to the project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Get the tool using the Tool model
    try:
        # First try with the provided ID
        tool = await Tool.find_one({"id": tool_id, "agent_id": agent_id})
        
        # If not found, try with _id field
        if not tool:
            tool = await Tool.find_one({"_id": tool_id, "agent_id": agent_id})
        
        # If still not found, try with ObjectId conversion
        if not tool:
            try:
                obj_id = ObjectId(tool_id)
                tool = await Tool.find_one({"_id": obj_id, "agent_id": agent_id})
            except Exception:
                tool = None
    except Exception:
        tool = None
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return ToolResponse(
        id=str(tool.id),
        agent_id=tool.agent_id,
        name=tool.name,
        tool_type=tool.tool_type,
        description=tool.description,
        provider=tool.provider,
        config=tool.config,
        enabled=tool.enabled,
        created_at=tool.created_at,
        updated_at=tool.updated_at
    )


@router.patch("/projects/{project_id}/agents/{agent_id}/tools/{tool_id}", response_model=ToolResponse)
async def update_agent_tool(project_id: str, agent_id: str, tool_id: str, tool_data: ToolUpdate):
    """Update a specific tool for an agent"""
    # Check if the agent exists and belongs to the project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Get the tool using the Tool model
    try:
        # First try with the provided ID
        tool = await Tool.find_one({"id": tool_id, "agent_id": agent_id})
        
        # If not found, try with _id field
        if not tool:
            tool = await Tool.find_one({"_id": tool_id, "agent_id": agent_id})
        
        # If still not found, try with ObjectId conversion
        if not tool:
            try:
                obj_id = ObjectId(tool_id)
                tool = await Tool.find_one({"_id": obj_id, "agent_id": agent_id})
            except Exception:
                tool = None
    except Exception:
        tool = None
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Update only the fields that are provided
    update_data = {k: v for k, v in tool_data.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        now = datetime.utcnow()
        update_data["updated_at"] = now
        
        # Update the tool attributes
        for key, value in update_data.items():
            setattr(tool, key, value)
        
        # Save the updated tool
        await tool.save()
        
        # Convert to response model
        return ToolResponse(
            id=str(tool.id),
            agent_id=tool.agent_id,
            name=tool.name,
            tool_type=tool.tool_type,
            description=tool.description,
            provider=tool.provider,
            config=tool.config,
            enabled=tool.enabled,
            created_at=tool.created_at,
            updated_at=tool.updated_at
        )
    
    # If no update was made, return the existing tool
    return ToolResponse(
        id=str(tool.id),
        agent_id=tool.agent_id,
        name=tool.name,
        tool_type=tool.tool_type,
        description=tool.description,
        provider=tool.provider,
        config=tool.config,
        enabled=tool.enabled,
        created_at=tool.created_at,
        updated_at=tool.updated_at
    )


@router.delete("/projects/{project_id}/agents/{agent_id}/tools/{tool_id}", status_code=204)
async def delete_agent_tool(project_id: str, agent_id: str, tool_id: str):
    """Delete a specific tool for an agent"""
    # Check if the agent exists and belongs to the project
    agent = await Agent.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Agent does not belong to the specified project")
    
    # Find the tool using the Tool model
    try:
        # First try with the provided ID
        tool = await Tool.find_one({"id": tool_id, "agent_id": agent_id})
        
        # If not found, try with _id field
        if not tool:
            tool = await Tool.find_one({"_id": tool_id, "agent_id": agent_id})
        
        # If still not found, try with ObjectId conversion
        if not tool:
            try:
                obj_id = ObjectId(tool_id)
                tool = await Tool.find_one({"_id": obj_id, "agent_id": agent_id})
            except Exception:
                tool = None
    except Exception:
        tool = None
    
    # If tool exists, delete it
    if tool:
        await tool.delete()
        return None
    else:
        raise HTTPException(status_code=404, detail="Tool not found")

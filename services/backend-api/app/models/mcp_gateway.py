import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel as PydanticBaseModel, Field
from app.models.base import BaseModel
from beanie import Indexed


class MCPToolStatus(str, Enum):
    """Enum for MCP tool status"""
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class MCPGatewayCreate(PydanticBaseModel):
    """Schema for creating an MCP gateway"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, description="API key for gateway access")


class MCPGatewayUpdate(PydanticBaseModel):
    """Schema for updating an MCP gateway"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, description="API key for gateway access")
    enabled: Optional[bool] = None


class MCPGateway(BaseModel):
    """MCP Gateway document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    project_id: str
    name: Indexed(str)
    description: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = False
    
    class Settings:
        name = "mcp_gateways"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "gateway_123",
                "project_id": "proj_456",
                "name": "Financial Analysis Gateway",
                "description": "Gateway for financial analysis tools",
                "api_key": "",
                "enabled": False,
                "created_at": "2025-08-20T10:48:52Z",
                "updated_at": "2025-08-20T10:48:52Z"
            }
        }


class MCPToolCreate(PydanticBaseModel):
    """Schema for creating an MCP tool from an agent"""
    agent_id: str = Field(..., description="Agent ID to convert to tool")


class MCPToolUpdate(PydanticBaseModel):
    """Schema for updating an MCP tool"""
    tool_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    input_schema: Optional[Dict[str, Any]] = None
    output_format: Optional[str] = None
    enabled: Optional[bool] = None


class MCPTool(BaseModel):
    """MCP Tool document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    gateway_id: str
    tool_name: str
    agent_id: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_format: Optional[str] = None
    status: MCPToolStatus = MCPToolStatus.GENERATING
    enabled: bool = False
    
    class Settings:
        name = "mcp_tools"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "tool_123",
                "gateway_id": "gateway_456",
                "tool_name": "analyze_financial_portfolio",
                "agent_id": "agent_789",
                "description": "Analyzes investment portfolios and provides recommendations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Portfolio data to analyze"}
                    },
                    "required": ["text"]
                },
                "output_format": "Structured analysis in markdown format",
                "status": "ready",
                "enabled": True,
                "created_at": "2025-08-20T10:48:52Z",
                "updated_at": "2025-08-20T10:48:52Z"
            }
        }


class MCPGatewayResponse(PydanticBaseModel):
    """Schema for MCP gateway response"""
    id: str
    project_id: str
    name: str
    description: Optional[str]
    api_key: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPToolResponse(PydanticBaseModel):
    """Schema for MCP tool response"""
    id: str
    gateway_id: str
    tool_name: str
    agent_id: str
    description: Optional[str]
    input_schema: Optional[Dict[str, Any]]
    output_format: Optional[str]
    status: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPGatewayList(PydanticBaseModel):
    """Schema for list of MCP gateways"""
    gateways: List[MCPGatewayResponse]


class MCPToolList(PydanticBaseModel):
    """Schema for list of MCP tools"""
    tools: List[MCPToolResponse]



class CreateInvocationRequest(PydanticBaseModel):
    """Request model for creating tool invocation"""
    arguments: Dict[str, Any] = Field(..., description="Input arguments for the tool")
    
    class Config:
        json_schema_extra = {
            "example": {
                "arguments": {
                    "text": "Analyze this portfolio data",
                    "risk_level": "moderate"
                }
            }
        }


class InvocationResponse(PydanticBaseModel):
    """Response model for tool invocation"""
    invocation_id: str = Field(..., description="Unique invocation identifier")
    user_task_id: str = Field(..., description="ID of the user input task")
    assistant_task_id: str = Field(..., description="ID of the assistant execution task")
    execution_time_seconds: Optional[float] = Field(None, description="Time taken for execution")
    error: Optional[str] = Field(None, description="Error message if invocation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "invocation_id": "inv_123",
                "user_task_id": "task_456",
                "assistant_task_id": "task_789",
                "execution_time_seconds": None,
                "error": None
            }
        }


class ToolInvocation(BaseModel):
    """Tool Invocation document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    tool_id: str
    user_task_id: str
    assistant_task_id: str
    execution_time_seconds: Optional[float] = None
    error: Optional[str] = None
    
    class Settings:
        name = "tool_invocations"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "inv_123",
                "tool_id": "tool_456",
                "user_task_id": "task_789",
                "assistant_task_id": "task_012",
                "execution_time_seconds": None,
                "error": None,
                "created_at": "2025-08-20T15:58:52Z",
                "updated_at": "2025-08-20T15:58:52Z"
            }
        }

import uuid
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from app.models.base import BaseModel
from beanie import Indexed

class ToolType(str, Enum):
    """Enum for tool types"""
    API = "api"
    MCP = "mcp"

class ProviderType(str, Enum):
    """Common providers for different tool types"""
    # API providers
    OPENAPI = "openapi"
    REST = "rest"
    GRAPHQL = "graphql"
    # MCP providers
    MCP_SERVICE = "mcp_service"
    # Other providers can be added as needed
    OTHER = "other"

class ToolCreate(PydanticBaseModel):
    """Schema for creating a tool"""
    name: str = Field(..., min_length=1, max_length=100)
    tool_type: ToolType
    description: Optional[str] = Field("", max_length=500)
    provider: Optional[str] = Field("", max_length=100, description="Provider for the tool (e.g., 'rest', 'openapi', 'mcp_service')")
    config: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific configuration including connection details and headers")
    enabled: bool = Field(True, description="Whether the tool is enabled")

    class Config:
        use_enum_values = True

class ToolUpdate(PydanticBaseModel):
    """Schema for updating a tool"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    provider: Optional[str] = Field(None, max_length=100)
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None

class Tool(BaseModel):
    """Tool document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    agent_id: str
    name: Indexed(str)
    tool_type: str  # Using string to allow for custom tool types beyond the enum
    description: Optional[str] = ""
    provider: Optional[str] = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    
    class Settings:
        name = "tools"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "examples": [
                {
                    "id": "c754f5e6-9a1d-4c83-8abb-5f3c32d9765d",
                    "agent_id": "b754f5e6-9a1d-4c83-8abb-5f3c32d9765d",
                    "name": "Weather API",
                    "tool_type": "api",
                    "description": "Integration with weather forecast API",
                    "provider": "rest",
                    "config": {
                        "base_url": "https://api.weather.com/v1",
                        "endpoints": {
                            "forecast": "/forecast",
                            "current": "/current"
                        },
                        "timeout": 30
                    },
                    "enabled": True,
                    "created_at": "2025-06-30T12:00:00Z",
                    "updated_at": "2025-06-30T12:00:00Z"
                },
                {
                    "id": "d854f5e6-9a1d-4c83-8abb-5f3c32d9765e",
                    "agent_id": "b754f5e6-9a1d-4c83-8abb-5f3c32d9765d",
                    "name": "Traffic Service",
                    "tool_type": "mcp",
                    "description": "MCP tool for traffic information",
                    "provider": "mcp_service",
                    "config": {
                        "server_url": "http://localhost:8010/mcp/",
                        "transport": "streamable_http"
                    },
                    "enabled": True,
                    "created_at": "2025-06-30T12:00:00Z",
                    "updated_at": "2025-06-30T12:00:00Z"
                }
            ]
        }

class ToolResponse(PydanticBaseModel):
    """Schema for tool responses"""
    id: str
    agent_id: str
    name: str
    tool_type: str
    description: Optional[str] = ""
    provider: Optional[str] = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    created_at: datetime
    updated_at: datetime

class ToolList(PydanticBaseModel):
    """Schema for listing tools"""
    tools: List[ToolResponse] = []

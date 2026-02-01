import uuid
import copy
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from app.models.base import BaseModel
from beanie import Indexed

# Message-related models have been moved to app/models/tasks.py

class AgentVersion(PydanticBaseModel):
    """Schema for a single agent version entry"""
    instructions: Optional[str] = Field(None, description="Instructions at this version")
    output_format: Optional[str] = Field(None, description="Output format at this version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(None, description="User who made this update")
    
    class Config:
        json_schema_extra = {
            "example": {
                "instructions": "Analyze customer data...",
                "output_format": "JSON with fields: analysis, recommendations",
                "created_at": "2025-11-10T14:30:00Z",
                "updated_by": "user@example.com"
            }
        }

class VersionHistoryResponse(PydanticBaseModel):
    """Schema for version history response"""
    versions: List[AgentVersion]
    total_count: int

class CapabilityType(str, Enum):
    """Enum for agent capabilities"""
    DATA_HARMONIZATION = "Data Harmonization"
    PIPELINE_OPTIMIZATION = "Pipeline Optimization"
    BUSINESS_INTELLIGENCE = "Business Intelligence"
    FEATURE_ENGINEERING = "Feature Engineering"
    DATA_DEBUGGING = "Data Debugging"
    DATA_UNDERSTANDING = "Data Understanding"

class AgentCreate(PydanticBaseModel):
    """Schema for creating a agent"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    owner: Optional[str] = Field(None, description="Owner or creator of the agent")
    instructions: Optional[str] = Field("", max_length=20000, description="Custom instructions for the agent")
    output_format: Optional[str] = Field("", max_length=2000, description="Expected format for the agent's output (e.g., text, json, markdown)")
    state: Optional[str] = Field("disabled", description="Agent state: enabled or disabled")
    deployed: Optional[bool] = Field(False, description="Whether the agent is deployed")
    api_key: Optional[str] = Field(None, description="API key for agent authentication")
    capabilities: Optional[List[CapabilityType]] = Field(default=None, description="List of agent capabilities")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the agent")

class AgentUpdate(PydanticBaseModel):
    """Schema for updating a agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    instructions: Optional[str] = Field(None, max_length=20000)
    output_format: Optional[str] = Field(None, max_length=2000)
    state: Optional[str] = Field(None, description="Agent state: enabled or disabled")
    deployed: Optional[bool] = Field(None, description="Whether the agent is deployed")
    api_key: Optional[str] = Field(None, description="API key for agent authentication")
    capabilities: Optional[List[CapabilityType]] = Field(default=None, description="List of agent capabilities")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the agent")
    updated_by: Optional[str] = Field(None, description="User ID who is making the update (for version history tracking)")

class Agent(BaseModel):
    """Agent document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    project_id: str
    name: Indexed(str)
    description: Optional[str] = None
    owner: Optional[str] = None
    task_count: int = 0
    instructions: Optional[str] = None
    output_format: str = ""
    state: str = "disabled"  # enabled or disabled
    deployed: bool = False
    api_key: Optional[str] = None
    capabilities: List[str] = []
    metadata: Dict[str, Any] = {}
    versions: List[Dict[str, Any]] = []
    
    def _add_version(self, instructions: str, output_format: str, updated_by: Optional[str] = None) -> None:
        """Add a version entry with the given instructions and output_format"""
        # Only create version if there's content to save
        if not instructions and not output_format:
            return
        
        timestamp = datetime.utcnow()
        version_entry = {
            "instructions": instructions,
            "output_format": output_format,
            "created_at": timestamp,
            "updated_by": updated_by
        }
        
        # Deep copy existing versions to prevent reference sharing issues
        # Without deep copy, datetime objects and nested dicts would be shared between
        # the new version_entry and existing versions, causing mutations to affect
        # multiple entries (e.g., all created_at timestamps becoming the same value)
        existing_versions = copy.deepcopy(self.versions)
        
        # Create new versions list with new version first, then existing versions
        self.versions = [version_entry] + existing_versions
        
        # Keep last 30 versions (newest first, oldest dropped)
        if len(self.versions) > 30:
            self.versions = self.versions[:30]
    
    class Settings:
        name = "agents"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "b754f5e6-9a1d-4c83-8abb-5f3c32d9765d",
                "project_id": "96df2786-5c9d-4427-9284-0a6c37e498ba",
                "name": "My Data Agent",
                "description": "Agent about our GitHub codebase",
                "owner": "user@example.com",
                "task_count": 10,
                "instructions": "agent instructions",
                "output_format": "",
                "state": "disabled",
                "deployed": False,
                "api_key": "api_1234567890abcdef",
                "capabilities": ["Data Understanding", "Business Intelligence"],
                "metadata": {
                    "mcp_gateways": [
                        {
                            "gateway_id": "gateway_123",
                            "tool_id": "tool_456",
                            "enabled_at": "2025-04-11T14:30:00Z"
                        },
                        {
                            "gateway_id": "gateway_789",
                            "tool_id": "tool_012",
                            "enabled_at": "2025-04-11T15:45:00Z"
                        }
                    ]
                },
                "created_at": "2025-04-11T14:00:00Z",
                "updated_at": "2025-04-11T15:00:00Z"
            }
        }

class AgentResponse(PydanticBaseModel):
    """Schema for agent response"""
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    task_count: int
    instructions: Optional[str] = None
    output_format: Optional[str] = ""
    state: str = "disabled"
    deployed: bool = False
    api_key: Optional[str] = None
    capabilities: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AgentList(PydanticBaseModel):
    """Schema for list of agents"""
    agents: List[AgentResponse]

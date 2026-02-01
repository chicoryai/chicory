import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field
from app.models.base import BaseModel
from beanie import Indexed


class EnvVariableCreate(PydanticBaseModel):
    """Schema for creating an environment variable"""
    key: str = Field(..., min_length=1, max_length=256, description="Environment variable name")
    value: str = Field(..., max_length=4096, description="Environment variable value")
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the variable")


class EnvVariableUpdate(PydanticBaseModel):
    """Schema for updating an environment variable"""
    key: Optional[str] = Field(None, min_length=1, max_length=256, description="Environment variable name")
    value: Optional[str] = Field(None, max_length=4096, description="Environment variable value")
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the variable")


class EnvVariable(BaseModel):
    """Environment variable document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    agent_id: Indexed(str)
    key: Indexed(str)
    value: str
    description: Optional[str] = None
    
    class Settings:
        name = "env_variables"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "e754f5e6-9a1d-4c83-8abb-5f3c32d9765d",
                "agent_id": "b754f5e6-9a1d-4c83-8abb-5f3c32d9765d",
                "key": "API_KEY",
                "value": "sk-1234567890abcdef",
                "description": "External API key for weather service",
                "created_at": "2025-06-30T12:00:00Z",
                "updated_at": "2025-06-30T12:00:00Z"
            }
        }


class EnvVariableResponse(PydanticBaseModel):
    """Schema for environment variable response"""
    id: str
    agent_id: str
    key: str
    value: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EnvVariableList(PydanticBaseModel):
    """Schema for listing environment variables"""
    env_variables: List[EnvVariableResponse] = []

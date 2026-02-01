from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from beanie import Document
from pydantic import BaseModel, Field

from app.models.base import BaseModel as ChicoryBaseModel


class Playground(Document):
    """Playground document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    agent_id: str
    project_id: str
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "playgrounds"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class PlaygroundInvocation(Document):
    """Playground Invocation document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    playground_id: str
    user_task_id: str
    assistant_task_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "playground_invocations"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


# Request/Response Models
class PlaygroundCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PlaygroundUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PlaygroundResponse(BaseModel):
    id: str
    agent_id: str
    project_id: str
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class PlaygroundList(BaseModel):
    playgrounds: list[PlaygroundResponse]
    has_more: bool


class InvocationCreate(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None


class InvocationResponse(BaseModel):
    invocation_id: str
    user_task_id: str
    assistant_task_id: str


class InvocationListItem(BaseModel):
    invocation_id: str
    user_task_id: str
    assistant_task_id: str
    created_at: datetime


class InvocationList(BaseModel):
    invocations: list[InvocationListItem]
    has_more: bool

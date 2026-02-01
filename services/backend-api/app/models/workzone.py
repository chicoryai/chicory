from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from beanie import Document
from pydantic import BaseModel, Field

from app.models.base import BaseModel as ChicoryBaseModel


class Workzone(Document):
    """Workzone document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    org_id: str
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "workzones"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class WorkzoneInvocation(Document):
    """Workzone Invocation document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    workzone_id: str
    project_id: str
    agent_id: str
    user_id: str
    user_task_id: str
    assistant_task_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "workzone_invocations"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


# Request/Response Models
class WorkzoneCreate(BaseModel):
    org_id: str = Field(..., min_length=1)
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkzoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkzoneResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class WorkzoneList(BaseModel):
    workzones: list[WorkzoneResponse]
    has_more: bool


class InvocationCreate(BaseModel):
    org_id: str
    project_id: str
    agent_id: str
    user_id: str
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
    org_id: str
    project_id: str
    agent_id: str
    user_id: str
    created_at: datetime


class InvocationList(BaseModel):
    invocations: list[InvocationListItem]
    has_more: bool

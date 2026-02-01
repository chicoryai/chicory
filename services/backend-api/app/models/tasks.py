import uuid
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from app.models.base import BaseModel
from beanie import Indexed

class TaskRole(str, Enum):
    """Enum for task roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class TaskStatus(str, Enum):
    """Enum for task processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskCreate(PydanticBaseModel):
    """Schema for creating a task"""
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class Task(BaseModel):
    """Task document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    agent_id: str
    project_id: Optional[str] = None
    role: TaskRole
    content: str
    status: Optional[TaskStatus] = None
    related_task_id: Optional[str] = None  # ID of the related task (user->assistant or assistant->user)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    completed_at: Optional[datetime] = None
    
    class Settings:
        name = "tasks"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "e7308965-bfe5-4d3b-a4be-f555d972a2c6",
                "agent_id": "a2f45e1c-3b7d-4ef9-8156-92d821d5845e",
                "project_id": "96df2786-5c9d-4427-9284-0a6c37e498ba",
                "role": "user",
                "content": "What are the main tables in our Databricks catalog?",
                "status": "completed",
                "metadata": {
                    "priority": "normal",
                    "source": "web_interface",
                    "queue_info": {
                        "queue_name": "chat_Tasks",
                        "task_id": "amq-12345678"
                    }
                },
                "created_at": "2025-04-11T15:30:00Z",
                "updated_at": "2025-04-11T15:30:05Z",
                "completed_at": "2025-04-11T15:30:10Z"
            }
        }

class TaskResponse(PydanticBaseModel):
    """Schema for Task response"""
    id: str
    agent_id: str
    project_id: Optional[str] = None
    role: str
    content: str
    status: Optional[str] = None
    related_task_id: Optional[str] = None  # ID of the related task (user->assistant or assistant->user)
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TaskList(PydanticBaseModel):
    """Schema for list of Tasks"""
    tasks: List[TaskResponse]
    has_more: bool = False

class TaskChunk(PydanticBaseModel):
    """Schema for task chunk in streaming response"""
    id: str
    content_chunk: str

class TaskComplete(PydanticBaseModel):
    """Schema for task completion notification"""
    id: str
    completed_at: datetime

class TaskFeedback(PydanticBaseModel):
    """Schema for submitting feedback on a task"""
    rating: str = Field(..., description="Feedback rating: must be 'positive' or 'negative'")
    feedback: Optional[str] = Field(None, description="Optional text feedback")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional tags to categorize feedback")
    
    @validator('rating')
    def validate_rating(cls, v):
        """Validate that rating is either 'positive' or 'negative'"""
        if v.lower() not in ['positive', 'negative']:
            raise ValueError("Rating must be 'positive' or 'negative'")
        return v.lower()

import uuid
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field
from beanie import Indexed
from app.models.base import BaseModel


class ConversationStatus(str, Enum):
    """Enum for conversation status"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConversationCreate(PydanticBaseModel):
    """Schema for creating a conversation"""
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Conversation(BaseModel):
    """Conversation document model for multi-turn conversations with Claude Agent SDK"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    project_id: Indexed(str)
    name: Optional[str] = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    message_count: int = 0
    session_id: Optional[str] = None  # ClaudeSDKClient session for resume
    last_session_id: Optional[str] = None  # Previous session for audit trail
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "conversations"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "c7308965-bfe5-4d3b-a4be-f555d972a2c6",
                "project_id": "96df2786-5c9d-4427-9284-0a6c37e498ba",
                "name": "Data Analysis Session",
                "status": "active",
                "message_count": 5,
                "session_id": "session_abc123",
                "last_session_id": "session_xyz789",
                "metadata": {
                    "source": "web_interface",
                    "tags": ["data-analysis", "databricks"]
                },
                "created_at": "2025-04-11T15:30:00Z",
                "updated_at": "2025-04-11T16:45:00Z"
            }
        }


class ConversationResponse(PydanticBaseModel):
    """Schema for Conversation response"""
    id: str
    project_id: str
    name: Optional[str] = None
    status: str
    message_count: int = 0
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationList(PydanticBaseModel):
    """Schema for list of Conversations"""
    conversations: List[ConversationResponse]
    has_more: bool = False
    total: int = 0


class ConversationUpdate(PydanticBaseModel):
    """Schema for updating a conversation"""
    name: Optional[str] = None
    status: Optional[ConversationStatus] = None
    metadata: Optional[Dict[str, Any]] = None

import uuid
from typing import Optional, Dict, Any, List, Union, Literal
from enum import Enum
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field
from beanie import Indexed
from app.models.base import BaseModel


class MessageRole(str, Enum):
    """Enum for message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """Enum for message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCall(PydanticBaseModel):
    """Schema for tool call within a message (legacy - deprecated)"""
    tool_name: str
    tool_id: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[str] = None
    is_error: bool = False


# Content Block Types (based on Anthropic Agent SDK)
class TextBlock(PydanticBaseModel):
    """Text content from the assistant."""
    type: Literal["text"] = "text"
    text: str


class ThinkingBlock(PydanticBaseModel):
    """Extended thinking content (for Opus 4.5 etc)."""
    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str = ""


class ToolUseBlock(PydanticBaseModel):
    """Fused tool invocation and result block."""
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Union[str, List[Dict[str, Any]]]] = None
    is_error: bool = False


# Union type for all content blocks
ContentBlock = Union[TextBlock, ThinkingBlock, ToolUseBlock]


class MessageCreate(PydanticBaseModel):
    """Schema for creating a message"""
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Message(BaseModel):
    """Message document model for conversation messages"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    conversation_id: Indexed(str)
    project_id: str
    role: MessageRole
    content_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    status: Optional[MessageStatus] = None
    parent_message_id: Optional[str] = None  # Links assistant message to user message
    turn_number: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    completed_at: Optional[datetime] = None

    class Settings:
        name = "messages"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "m7308965-bfe5-4d3b-a4be-f555d972a2c6",
                "conversation_id": "c7308965-bfe5-4d3b-a4be-f555d972a2c6",
                "project_id": "96df2786-5c9d-4427-9284-0a6c37e498ba",
                "role": "user",
                "content_blocks": [
                    {"type": "text", "text": "What are the main tables in our Databricks catalog?"}
                ],
                "status": "completed",
                "parent_message_id": None,
                "turn_number": 1,
                "metadata": {
                    "source": "web_interface"
                },
                "created_at": "2025-04-11T15:30:00Z",
                "updated_at": "2025-04-11T15:30:05Z",
                "completed_at": "2025-04-11T15:30:10Z"
            }
        }


class MessageResponse(PydanticBaseModel):
    """Schema for Message response"""
    id: str
    conversation_id: str
    project_id: str
    role: str
    content_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    status: Optional[str] = None
    parent_message_id: Optional[str] = None
    turn_number: int = 0
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageList(PydanticBaseModel):
    """Schema for list of Messages"""
    messages: List[MessageResponse]
    has_more: bool = False
    total: int = 0


class MessageChunk(PydanticBaseModel):
    """Schema for message chunk in streaming response"""
    id: str
    content_chunk: str


class MessageComplete(PydanticBaseModel):
    """Schema for message completion notification"""
    id: str
    completed_at: datetime
    session_id: Optional[str] = None


class SendMessageRequest(PydanticBaseModel):
    """Schema for sending a new message to conversation"""
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

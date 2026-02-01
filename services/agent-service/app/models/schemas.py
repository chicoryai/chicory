from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SandboxNetworkConfig(BaseModel):
    """Sandbox network configuration."""
    allow_local_binding: bool = True
    allow_unix_sockets: List[str] = []


class SandboxConfig(BaseModel):
    """Sandbox configuration for agent execution."""
    enabled: bool = True
    auto_allow_bash_if_sandboxed: bool = True
    excluded_commands: List[str] = []
    allow_unsandboxed_commands: bool = False
    network: Optional[SandboxNetworkConfig] = None


class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    url: str
    type: str = "http"
    headers: Dict[str, str] = {}
    timeout: int = 300000


class AgentConfig(BaseModel):
    """Configuration for the Claude agent."""
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = []
    mcp_servers: Dict[str, MCPServerConfig] = {}
    sandbox: Optional[SandboxConfig] = None
    max_turns: int = 150
    model: Optional[str] = None
    cwd: Optional[str] = None
    add_dirs: List[str] = []
    # Workspace configuration
    working_directory: Optional[str] = None  # Working directory path from backend-api
    context_directory: Optional[str] = None  # Read-only context/data path


class SendMessageRequest(BaseModel):
    """Request to send a message to the conversation."""
    content: str
    message_id: str
    project_id: str
    agent_id: Optional[str] = None  # Optional - conversations are project-scoped
    session_id: Optional[str] = None
    agent_config: AgentConfig = AgentConfig()


class StreamingInputChunk(BaseModel):
    """A chunk of streaming input."""
    type: str = "text"
    text: str


class SendMessageStreamingRequest(BaseModel):
    """Request to send a message with streaming input."""
    message_id: str
    project_id: str
    agent_id: Optional[str] = None  # Optional - conversations are project-scoped
    session_id: Optional[str] = None
    agent_config: AgentConfig = AgentConfig()


class InterruptRequest(BaseModel):
    """Request to interrupt an active response."""
    message_id: str


class MessageResponse(BaseModel):
    """Response containing message result."""
    message_id: str
    session_id: Optional[str] = None
    status: str
    content: Optional[str] = None
    error: Optional[str] = None


class SessionInfo(BaseModel):
    """Information about an active session."""
    session_id: str
    conversation_id: str
    project_id: str
    agent_id: Optional[str] = None
    created_at: str
    last_activity: str


class SessionListResponse(BaseModel):
    """Response containing list of active sessions."""
    sessions: List[SessionInfo]
    total: int

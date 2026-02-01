"""
Unified ClaudeAgentOptions builder.

Provides a consistent way to build ClaudeAgentOptions across services.
Based on patterns from agent-service/claude_agent.py and inference-worker/adaptive_rag.py.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional: Claude Agent SDK imports
try:
    from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    ClaudeAgentOptions = None
    AgentDefinition = None


@dataclass
class AgentSettings:
    """Settings configuration for Claude Agent SDK."""

    permissions: Dict[str, Any] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string for ClaudeAgentOptions."""
        settings = {}
        if self.permissions:
            settings["permissions"] = self.permissions
        if self.env:
            settings["env"] = self.env
        return json.dumps(settings)


class AgentOptionsBuilder:
    """
    Builder for ClaudeAgentOptions with sensible defaults.

    Example:
        builder = AgentOptionsBuilder(working_directory="/tmp/workspace")
        builder.with_mcp_servers({"db-mcp": {...}})
        builder.with_subagents({"reader": AgentDefinition(...)})
        options = builder.build()
    """

    # Default base tools
    DEFAULT_TOOLS = ["Python", "Bash", "Read", "Write", "Skill"]

    def __init__(
        self,
        working_directory: str,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 100,
    ):
        """
        Initialize the builder.

        Args:
            working_directory: The working directory for agent execution.
            model: The Claude model to use.
            max_turns: Maximum number of turns for the conversation.
        """
        self.working_directory = working_directory
        self.model = model
        self.max_turns = max_turns

        self._tools: List[str] = list(self.DEFAULT_TOOLS)
        self._mcp_servers: Dict[str, Any] = {}
        self._subagents: Dict[str, Any] = {}
        self._system_prompt: str = ""
        self._context_directories: List[str] = []
        self._resume_session_id: Optional[str] = None
        self._settings = AgentSettings()
        self._mcp_permission_patterns: List[str] = []

    def with_tools(self, tools: List[str]) -> "AgentOptionsBuilder":
        """Add additional tools to the allowed tools list."""
        self._tools.extend(tools)
        return self

    def with_mcp_servers(self, servers: Dict[str, Any]) -> "AgentOptionsBuilder":
        """
        Configure MCP servers.

        Args:
            servers: Dict mapping server names to server configs.
                     Each config should have 'type', 'url', and optionally 'headers'.
        """
        self._mcp_servers = servers

        # Build wildcard permission patterns for each server
        for server_name in servers.keys():
            normalized_name = server_name.replace(' ', '_').replace('-', '_')
            pattern = f"mcp__{normalized_name}__*"
            self._mcp_permission_patterns.append(pattern)

        return self

    def with_subagents(self, agents: Dict[str, Any]) -> "AgentOptionsBuilder":
        """Configure subagents for specialized tasks."""
        self._subagents = agents
        return self

    def with_system_prompt(self, prompt: str) -> "AgentOptionsBuilder":
        """Set the system prompt."""
        self._system_prompt = prompt
        return self

    def with_system_prompt_file(self, file_path: str) -> "AgentOptionsBuilder":
        """Load system prompt from a file."""
        path = Path(file_path)
        if path.exists():
            self._system_prompt = path.read_text()
        return self

    def with_context_directories(self, directories: List[str]) -> "AgentOptionsBuilder":
        """Add context directories that the agent can read from."""
        self._context_directories = directories
        return self

    def with_resume_session(self, session_id: str) -> "AgentOptionsBuilder":
        """Configure to resume an existing session."""
        self._resume_session_id = session_id
        return self

    def with_permissions(
        self,
        allow: Optional[List[str]] = None,
        deny: Optional[List[str]] = None,
    ) -> "AgentOptionsBuilder":
        """
        Configure tool permissions.

        Args:
            allow: List of tool patterns to allow (e.g., ["Bash", "mcp__*"])
            deny: List of tool patterns to deny
        """
        if allow:
            self._settings.permissions["allow"] = allow
        if deny:
            self._settings.permissions["deny"] = deny
        return self

    def with_env_variables(self, env: Dict[str, str]) -> "AgentOptionsBuilder":
        """Set environment variables for the agent."""
        self._settings.env.update(env)
        return self

    def build(self) -> "ClaudeAgentOptions":
        """Build and return the ClaudeAgentOptions."""
        if not CLAUDE_SDK_AVAILABLE:
            raise ImportError(
                "claude-agent-sdk is required for AgentOptionsBuilder. "
                "Install with: pip install claude-agent-sdk"
            )

        # Build permissions with MCP patterns
        if self._mcp_permission_patterns:
            current_allow = self._settings.permissions.get("allow", [])
            self._settings.permissions["allow"] = current_allow + self._mcp_permission_patterns

        # Build the options dict
        options_kwargs: Dict[str, Any] = {
            "allowed_tools": self._tools,
            "cwd": self.working_directory,
            "model": self.model,
            "max_turns": self.max_turns,
        }

        if self._system_prompt:
            options_kwargs["system_prompt"] = self._system_prompt

        if self._mcp_servers:
            options_kwargs["mcp_servers"] = self._mcp_servers

        if self._subagents:
            options_kwargs["agents"] = self._subagents

        if self._context_directories:
            options_kwargs["add_dirs"] = self._context_directories

        if self._resume_session_id:
            options_kwargs["resume"] = self._resume_session_id

        # Build settings JSON
        settings_json = self._settings.to_json()
        if settings_json != "{}":
            options_kwargs["settings"] = settings_json

        return ClaudeAgentOptions(**options_kwargs)

    def build_dict(self) -> Dict[str, Any]:
        """Build and return options as a dictionary (for debugging/logging)."""
        return {
            "allowed_tools": self._tools,
            "cwd": self.working_directory,
            "model": self.model,
            "max_turns": self.max_turns,
            "system_prompt_length": len(self._system_prompt),
            "mcp_servers": list(self._mcp_servers.keys()),
            "subagents": list(self._subagents.keys()),
            "context_directories": self._context_directories,
            "resume_session_id": self._resume_session_id,
        }

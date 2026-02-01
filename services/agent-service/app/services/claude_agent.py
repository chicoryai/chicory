"""
Claude Agent SDK wrapper for conversation management.

Manages Claude SDK client sessions with workspace isolation,
Chicory MCP integration, and dynamic configuration.
"""
import asyncio
import logging
import traceback
from typing import Any, AsyncIterator, Dict, List, Optional
from dataclasses import dataclass, field

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    UserMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    HookMatcher,
    HookContext,
    HookInput,
    HookJSONOutput,
)

from pathlib import Path

from app.core.config import settings, CHICORY_MCP_TOOLS, DB_MCP_TOOLS, TOOLS_MCP_TOOLS, get_tool_active_description
from app.models.schemas import AgentConfig, SandboxConfig
from app.services.workspace import WorkspaceManager, WorkspaceConfig
from app.services.prompt_builder import build_settings_json
from app.services.session_cache import SessionCache

logger = logging.getLogger(__name__)

# Path to the source CLAUDE.md system prompt
SOURCE_CLAUDE_MD = Path(__file__).parent.parent.parent / ".claude" / "CLAUDE.md"


@dataclass
class StreamingEvent:
    """Event emitted during message streaming."""
    event_type: str  # message_chunk, thinking, tool_use, tool_result, user_message, result, error
    data: Dict[str, Any]
    session_id: Optional[str] = None


class ConversationAgentManager:
    """
    Manages Claude SDK client sessions for continuous conversations.

    Features:
    - Isolated workspace per conversation
    - .claude folder with CLAUDE.md, settings.json, skills
    - Chicory Platform MCP integration
    - Dynamic system prompt with project context
    - Sandbox and permissions configuration

    Session management pattern:
    - Sessions are created automatically on first query
    - Session IDs are captured from ResultMessage
    - Resume option continues from previous session
    """

    def __init__(
        self,
        project_id: str,
        conversation_id: str,
        agent_id: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,
        session_cache: Optional[SessionCache] = None,
    ):
        self.project_id = project_id
        self.conversation_id = conversation_id
        self.agent_id = agent_id  # Optional - conversations are project-scoped
        self.agent_config = agent_config or AgentConfig()
        self.session_cache = session_cache
        self.client: Optional[ClaudeSDKClient] = None
        self.session_id: Optional[str] = None
        self._is_connected = False
        self._stderr_buffer: List[str] = []  # Capture stderr for error detection
        self._tool_descriptions: Dict[str, str] = {}  # tool_use_id -> active_description (populated by PreToolUse hook)

        # Workspace management
        self.workspace_manager: Optional[WorkspaceManager] = None
        self.workspace_config: Optional[WorkspaceConfig] = None

    def _stderr_handler(self, message: str) -> None:
        """Capture stderr output for error detection."""
        self._stderr_buffer.append(message)
        logger.debug(f"[CLAUDE_AGENT] stderr: {message}")

    def _check_stale_session_in_stderr(self) -> bool:
        """Check if stderr contains stale session error."""
        for line in self._stderr_buffer:
            if "No conversation found with session ID" in line:
                return True
        return False

    def _clear_stderr_buffer(self) -> None:
        """Clear the stderr buffer."""
        self._stderr_buffer = []

    async def initialize(self, session_id: Optional[str] = None) -> None:
        """
        Initialize or resume a conversation session.

        Sets up the workspace, builds configuration, and connects to Claude SDK.
        If session_cache is provided, attempts to resume from cached session.
        If resume fails, clears cache and starts fresh.

        Args:
            session_id: If provided, resumes the existing session.
                       If None, checks cache then creates a new session.
        """
        logger.info(f"[CLAUDE_AGENT] Initializing conversation: project={self.project_id}, conversation={self.conversation_id}")

        # Try to restore session_id from cache if not provided
        cached_session_id = None
        if self.session_cache and not session_id:
            cached_session_id = await self.session_cache.get_session_id(self.conversation_id)
            if cached_session_id:
                session_id = cached_session_id
                logger.info(f"[CLAUDE_AGENT] Will attempt to resume from cached session: {session_id}")

        # Get MCP configuration with project-specific endpoints for DB and Tools MCP
        mcp_servers = settings.get_all_mcp_config(self.project_id)

        # Build list of allowed MCP tools based on configured servers
        mcp_tools = []
        if settings.get_chicory_mcp_config():
            mcp_tools.extend(CHICORY_MCP_TOOLS)
        if settings.DB_MCP_SERVER_URL:
            mcp_tools.extend(DB_MCP_TOOLS)
        if settings.TOOLS_MCP_SERVER_URL:
            mcp_tools.extend(TOOLS_MCP_TOOLS)

        # Setup workspace (creates directories and .claude folder with MCP config)
        logger.info("[CLAUDE_AGENT] Setting up workspace...")
        self.workspace_manager = WorkspaceManager(
            project_id=self.project_id,
            conversation_id=self.conversation_id,
            base_path=settings.WORKSPACE_BASE_PATH,
            mcp_servers=mcp_servers,
            mcp_tools=mcp_tools,
        )
        self.workspace_config = await self.workspace_manager.setup()
        logger.info(f"[CLAUDE_AGENT] Workspace ready: {self.workspace_config.working_directory}")

        # Build agent options and connect (with retry on stale session)
        await self._connect_with_retry(session_id, cached_session_id)

    async def _connect_with_retry(
        self,
        session_id: Optional[str],
        cached_session_id: Optional[str]
    ) -> None:
        """
        Connect to Claude SDK with automatic retry on stale session.

        If resuming a cached session fails, clears the cache and retries
        with a fresh session.

        Args:
            session_id: Session ID to resume (if any)
            cached_session_id: The session ID from cache (for cleanup on failure)
        """
        # Build agent options
        logger.info("[CLAUDE_AGENT] Building agent options...")
        options = await self._build_agent_options(session_id)
        logger.info(f"[CLAUDE_AGENT] Options built with {len(options.allowed_tools)} tools")

        # Create and connect client
        logger.info("[CLAUDE_AGENT] Creating ClaudeSDKClient...")
        self.client = ClaudeSDKClient(options=options)

        try:
            logger.info("[CLAUDE_AGENT] Connecting to Claude SDK...")
            await self.client.connect()
            logger.info("[CLAUDE_AGENT] Client connected successfully")
            self._is_connected = True
            self.session_id = session_id

        except Exception as e:
            error_msg = str(e)
            # Check stderr if available (ProcessError has stderr attribute)
            stderr_msg = getattr(e, 'stderr', '') or ''

            logger.error(f"[CLAUDE_AGENT] Connection error: {error_msg}")
            logger.error(f"[CLAUDE_AGENT] Exception type: {type(e).__name__}")
            logger.error(f"[CLAUDE_AGENT] Full traceback:\n{traceback.format_exc()}")
            if stderr_msg:
                logger.error(f"[CLAUDE_AGENT] stderr from exception: {stderr_msg}")
            if self._stderr_buffer:
                logger.error(f"[CLAUDE_AGENT] stderr buffer: {self._stderr_buffer}")

            # Log additional context for debugging
            print(f"[CLAUDE_AGENT] ========== CONNECTION ERROR ==========")
            print(f"[CLAUDE_AGENT] Error: {error_msg}")
            print(f"[CLAUDE_AGENT] Exception type: {type(e).__name__}")
            print(f"[CLAUDE_AGENT] Session ID attempted: {session_id}")
            print(f"[CLAUDE_AGENT] Cached session ID: {cached_session_id}")
            print(f"[CLAUDE_AGENT] Working directory: {self.workspace_config.working_directory if self.workspace_config else 'N/A'}")
            print(f"[CLAUDE_AGENT] Full traceback:\n{traceback.format_exc()}")
            print(f"[CLAUDE_AGENT] =======================================")

            # Check if this is a stale session error (check exception, stderr attr, and stderr buffer)
            is_stale_session = cached_session_id and (
                "No conversation found with session ID" in error_msg or
                "No conversation found with session ID" in stderr_msg or
                self._check_stale_session_in_stderr()
            )

            if is_stale_session:
                logger.warning(f"[CLAUDE_AGENT] Cached session {cached_session_id} is stale, clearing and retrying...")

                # Clear stale session from cache
                if self.session_cache:
                    await self.session_cache.delete(self.conversation_id)
                    logger.info(f"[CLAUDE_AGENT] Cleared stale session from cache")

                # Clear stderr buffer and retry without resume option
                self._clear_stderr_buffer()
                logger.info("[CLAUDE_AGENT] Retrying with fresh session...")
                options = await self._build_agent_options(None)  # No session_id = fresh session
                self.client = ClaudeSDKClient(options=options)
                await self.client.connect()
                logger.info("[CLAUDE_AGENT] Client connected successfully (fresh session)")
                self._is_connected = True
                self.session_id = None  # Will be captured from ResultMessage
            else:
                # Not a stale session error, re-raise
                raise

    async def _build_agent_options(
        self,
        session_id: Optional[str] = None
    ) -> ClaudeAgentOptions:
        """
        Build ClaudeAgentOptions with full configuration.

        Includes:
        - Base tools (Python, Bash, Read, Write, Skill)
        - Chicory MCP tools (if configured)
        - Dynamic system prompt with project context
        - Sandbox and permissions settings
        """
        # 1. Base tools (BrewHub pattern)
        allowed_tools = ["Python", "Bash", "Read", "Write", "Skill"]
        print(f"[CLAUDE_AGENT] Base tools: {allowed_tools}")

        # 2. Add MCP tools based on configured servers
        mcp_servers = settings.get_all_mcp_config(self.project_id)
        print(f"[CLAUDE_AGENT] MCP servers configured: {list(mcp_servers.keys()) if mcp_servers else 'none'}")

        # Add Chicory MCP tools if configured
        if settings.get_chicory_mcp_config():
            allowed_tools.extend(CHICORY_MCP_TOOLS)
            print(f"[CLAUDE_AGENT] Added {len(CHICORY_MCP_TOOLS)} Chicory MCP tools")
            logger.info(f"[CLAUDE_AGENT] Added {len(CHICORY_MCP_TOOLS)} Chicory MCP tools")

        # Add DB MCP tools if configured
        if settings.DB_MCP_SERVER_URL:
            allowed_tools.extend(DB_MCP_TOOLS)
            print(f"[CLAUDE_AGENT] Added DB MCP tools (project: {self.project_id})")
            logger.info(f"[CLAUDE_AGENT] Added DB MCP tools for project {self.project_id}")

        # Add Tools MCP tools if configured
        if settings.TOOLS_MCP_SERVER_URL:
            allowed_tools.extend(TOOLS_MCP_TOOLS)
            print(f"[CLAUDE_AGENT] Added Tools MCP tools (project: {self.project_id})")
            logger.info(f"[CLAUDE_AGENT] Added Tools MCP tools for project {self.project_id}")

        # 3. Load system prompt from CLAUDE.md
        system_prompt = ""
        if SOURCE_CLAUDE_MD.exists():
            system_prompt = SOURCE_CLAUDE_MD.read_text()
            print(f"[CLAUDE_AGENT] Loaded system prompt from {SOURCE_CLAUDE_MD} ({len(system_prompt)} chars)")
        else:
            logger.warning(f"[CLAUDE_AGENT] CLAUDE.md not found at {SOURCE_CLAUDE_MD}")
            print(f"[CLAUDE_AGENT] WARNING: CLAUDE.md not found at {SOURCE_CLAUDE_MD}")

        # 4. Build settings/sandbox configuration
        settings_json = build_settings_json(
            working_directory=self.workspace_config.working_directory,
            mcp_tools=CHICORY_MCP_TOOLS if mcp_servers else [],
        )

        # 5. Build options dictionary
        options_kwargs = {
            "allowed_tools": allowed_tools,
            "system_prompt": system_prompt,
            "settings": settings_json,
            "cwd": self.workspace_config.working_directory,
            "max_turns": self.agent_config.max_turns or settings.DEFAULT_MAX_TURNS,
            "model": self.agent_config.model or settings.DEFAULT_MODEL,
            "stderr": self._stderr_handler,  # Capture stderr for error detection
        }

        # 6. Add MCP servers if configured
        if mcp_servers:
            options_kwargs["mcp_servers"] = mcp_servers
            logger.info(f"[CLAUDE_AGENT] MCP servers configured: {list(mcp_servers.keys())}")

        # 7. Add context directory if specified
        if self.agent_config.context_directory:
            options_kwargs["add_dirs"] = [self.agent_config.context_directory]

        # 8. Resume existing session if provided
        if session_id:
            options_kwargs["resume"] = session_id
            logger.info(f"[CLAUDE_AGENT] Resuming session: {session_id}")

        # 9. Add PreToolUse hook for active descriptions
        # TEMPORARILY DISABLED - investigating MCP tool discovery issue
        # TODO: Re-enable once MCP tools work correctly
        # # Create a closure to capture self for the hook callback
        # tool_descriptions = self._tool_descriptions
        #
        # async def pre_tool_use_hook(
        #     input_data: HookInput,
        #     tool_use_id: Optional[str],
        #     context: HookContext
        # ) -> HookJSONOutput:
        #     tool_name = getattr(input_data, 'tool_name', '')
        #     tool_input = getattr(input_data, 'tool_input', {})
        #     active_description = get_tool_active_description(tool_name, tool_input)
        #     if tool_use_id:
        #         tool_descriptions[tool_use_id] = active_description
        #         logger.debug(f"[CLAUDE_AGENT] PreToolUse hook: {tool_name} -> {active_description}")
        #     return {}
        #
        # options_kwargs["hooks"] = {
        #     'PreToolUse': [
        #         HookMatcher(
        #             matcher=None,  # Match all tools
        #             hooks=[pre_tool_use_hook]
        #         )
        #     ]
        # }
        # logger.info("[CLAUDE_AGENT] PreToolUse hook registered for active descriptions")

        # Log complete options for debugging
        print(f"[CLAUDE_AGENT] ========== CLAUDE AGENT OPTIONS ==========")
        print(f"[CLAUDE_AGENT] allowed_tools ({len(allowed_tools)}): {allowed_tools}")
        print(f"[CLAUDE_AGENT] model: {options_kwargs.get('model')}")
        print(f"[CLAUDE_AGENT] max_turns: {options_kwargs.get('max_turns')}")
        print(f"[CLAUDE_AGENT] cwd: {options_kwargs.get('cwd')}")
        print(f"[CLAUDE_AGENT] resume session_id: {session_id or 'None (new session)'}")
        if mcp_servers:
            print(f"[CLAUDE_AGENT] mcp_servers: {list(mcp_servers.keys())}")
            for server_name, server_config in mcp_servers.items():
                print(f"[CLAUDE_AGENT]   {server_name}:")
                print(f"[CLAUDE_AGENT]     type: {server_config.get('type')}")
                print(f"[CLAUDE_AGENT]     url: {server_config.get('url')}")
                # Show headers with masked auth values
                headers = server_config.get('headers', {})
                masked_headers = {}
                for k, v in headers.items():
                    if k.lower() == 'authorization' and v:
                        # Show first 15 chars + last 4 chars of auth header
                        if len(v) > 20:
                            masked_headers[k] = f"{v[:15]}...{v[-4:]}"
                        else:
                            masked_headers[k] = "***"
                    else:
                        masked_headers[k] = v
                print(f"[CLAUDE_AGENT]     headers: {masked_headers}")
        else:
            print(f"[CLAUDE_AGENT] mcp_servers: None")
        if self.agent_config.context_directory:
            print(f"[CLAUDE_AGENT] add_dirs: {options_kwargs.get('add_dirs')}")
        print(f"[CLAUDE_AGENT] system_prompt: {len(system_prompt)} chars from {SOURCE_CLAUDE_MD}")
        print(f"[CLAUDE_AGENT] settings length: {len(settings_json)} chars")
        print(f"[CLAUDE_AGENT] ============================================")

        return ClaudeAgentOptions(**options_kwargs)

    async def send_message(
        self,
        content: str,
        message_id: str,
    ) -> AsyncIterator[StreamingEvent]:
        """
        Send a message and stream the response.

        Args:
            content: The user message content
            message_id: Unique identifier for this message exchange

        Yields:
            StreamingEvent objects containing response chunks
        """
        if not self.client or not self._is_connected:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        try:
            await self.client.query(content, session_id=self.session_id or "default")

            message_count = 0
            async for message in self.client.receive_response():
                message_count += 1
                print(f"[CLAUDE_AGENT] Received message #{message_count} from SDK")

                events = self._process_message(message)
                print(f"[CLAUDE_AGENT] Generated {len(events)} events from message #{message_count}")

                for event in events:
                    logger.info(f"[CLAUDE_AGENT] Yielding event: type={event.event_type}, session_id={event.session_id}")
                    logger.debug(f"[CLAUDE_AGENT] Event data: {event.data}")
                    yield event

                # Capture session_id from result message
                if isinstance(message, ResultMessage):
                    self.session_id = message.session_id

                    # Cache session_id for future resume
                    if self.session_cache and self.session_id:
                        await self.session_cache.set_session_id(
                            self.conversation_id,
                            self.session_id
                        )

                    result_event = StreamingEvent(
                        event_type="result",
                        data={
                            "message_id": message_id,
                            "duration_ms": message.duration_ms,
                            "num_turns": message.num_turns,
                            "is_error": message.is_error,
                            "result": message.result,
                        },
                        session_id=self.session_id,
                    )
                    logger.info(f"[CLAUDE_AGENT] Yielding result event: session_id={self.session_id}, num_turns={message.num_turns}, duration_ms={message.duration_ms}")
                    logger.debug(f"[CLAUDE_AGENT] Result data: {result_event.data}")
                    yield result_event

            # Log summary after all messages processed
            print(f"[CLAUDE_AGENT] ========== MESSAGE PROCESSING COMPLETE ==========")
            print(f"[CLAUDE_AGENT] Total messages received from SDK: {message_count}")
            print(f"[CLAUDE_AGENT] ==================================================")

        except Exception as e:
            error_msg = str(e)
            stderr_msg = getattr(e, 'stderr', '') or ''

            logger.error(f"[CLAUDE_AGENT] Error processing message: {error_msg}")
            if stderr_msg:
                logger.error(f"[CLAUDE_AGENT] stderr from exception: {stderr_msg}")
            if self._stderr_buffer:
                logger.error(f"[CLAUDE_AGENT] stderr buffer: {self._stderr_buffer}")

            # Check if this is a stale session error
            is_stale_session = self.session_id and (
                "No conversation found with session ID" in error_msg or
                "No conversation found with session ID" in stderr_msg or
                self._check_stale_session_in_stderr()
            )

            if is_stale_session and self.session_cache:
                logger.warning(f"[CLAUDE_AGENT] Session {self.session_id} is stale, clearing from cache")
                await self.session_cache.delete(self.conversation_id)
                # Mark session as invalid so next request starts fresh
                self.session_id = None

            error_event = StreamingEvent(
                event_type="error",
                data={
                    "message_id": message_id,
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "is_stale_session": is_stale_session,
                },
            )
            logger.error(f"[CLAUDE_AGENT] Yielding error event: {error_event.data}")
            yield error_event
            raise

    def _process_message(self, message: Any) -> List[StreamingEvent]:
        """Convert SDK message to streaming events."""
        events = []

        # Log the raw message structure for debugging
        print(f"[CLAUDE_AGENT] ========== PROCESSING MESSAGE ==========")
        print(f"[CLAUDE_AGENT] Message type: {type(message).__name__}")
        print(f"[CLAUDE_AGENT] Message attributes: {list(message.__dict__.keys()) if hasattr(message, '__dict__') else 'N/A'}")

        if isinstance(message, AssistantMessage):
            print(f"[CLAUDE_AGENT] AssistantMessage has {len(message.content)} content blocks")
            for i, block in enumerate(message.content):
                block_type = type(block).__name__
                print(f"[CLAUDE_AGENT]   Block {i}: {block_type}")
                # Log raw block attributes for debugging
                if hasattr(block, '__dict__'):
                    attrs = block.__dict__
                    print(f"[CLAUDE_AGENT]     Attributes: {list(attrs.keys())}")
                    # Log specific values for debugging
                    for key, value in attrs.items():
                        # Truncate long values
                        val_str = str(value)
                        if len(val_str) > 200:
                            val_str = val_str[:200] + "..."
                        print(f"[CLAUDE_AGENT]       {key}: {val_str}")
        elif isinstance(message, UserMessage):
            content = message.content
            content_desc = f"{len(content)} blocks" if isinstance(content, list) else f"string ({len(content)} chars)"
            print(f"[CLAUDE_AGENT] UserMessage has {content_desc}")
            if message.parent_tool_use_id:
                print(f"[CLAUDE_AGENT]   parent_tool_use_id: {message.parent_tool_use_id}")
        else:
            # Log non-AssistantMessage/UserMessage types fully
            if hasattr(message, '__dict__'):
                print(f"[CLAUDE_AGENT] Message content: {message.__dict__}")
        print(f"[CLAUDE_AGENT] ========================================")

        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    events.append(StreamingEvent(
                        event_type="message_chunk",
                        data={
                            "type": "text",
                            "text": block.text,
                        },
                    ))
                elif isinstance(block, ThinkingBlock):
                    events.append(StreamingEvent(
                        event_type="thinking",
                        data={
                            "type": "thinking",
                            "thinking": block.thinking,
                            "signature": getattr(block, 'signature', ''),
                        },
                    ))
                elif isinstance(block, ToolUseBlock):
                    # Log MCP tool invocations for debugging
                    is_mcp_tool = block.name.startswith("mcp__")

                    # Get active description from hook-populated dictionary
                    active_description = self._tool_descriptions.pop(block.id, None)

                    # Fallback if hook didn't fire (shouldn't happen, but be safe)
                    if not active_description:
                        active_description = get_tool_active_description(block.name, block.input)

                    if is_mcp_tool:
                        logger.info(f"[CLAUDE_AGENT] MCP tool invoked: {block.name}")
                        print(f"[CLAUDE_AGENT] MCP TOOL CALL: {block.name}")
                        print(f"[CLAUDE_AGENT]   tool_id: {block.id}")
                        print(f"[CLAUDE_AGENT]   input: {block.input}")
                        print(f"[CLAUDE_AGENT]   active_description: {active_description}")

                    events.append(StreamingEvent(
                        event_type="tool_use",
                        data={
                            "tool_name": block.name,
                            "tool_id": block.id,
                            "input": block.input,
                            "is_mcp_tool": is_mcp_tool,
                            "active_description": active_description,
                        },
                    ))
                elif isinstance(block, ToolResultBlock):
                    # Log tool results, especially errors
                    if block.is_error:
                        logger.error(f"[CLAUDE_AGENT] Tool error for {block.tool_use_id}: {block.content}")
                        print(f"[CLAUDE_AGENT] TOOL ERROR:")
                        print(f"[CLAUDE_AGENT]   tool_id: {block.tool_use_id}")
                        print(f"[CLAUDE_AGENT]   error: {block.content}")
                    else:
                        logger.debug(f"[CLAUDE_AGENT] Tool result for {block.tool_use_id}: {str(block.content)[:200]}...")
                    events.append(StreamingEvent(
                        event_type="tool_result",
                        data={
                            "tool_id": block.tool_use_id,
                            "output": block.content,
                            "is_error": block.is_error,
                        },
                    ))

        elif isinstance(message, UserMessage):
            # UserMessage contains tool results linked via parent_tool_use_id
            content = message.content
            if isinstance(content, list):
                # Process content blocks within UserMessage
                for block in content:
                    if isinstance(block, ToolResultBlock):
                        if block.is_error:
                            logger.error(f"[CLAUDE_AGENT] Tool error for {block.tool_use_id}: {block.content}")
                        events.append(StreamingEvent(
                            event_type="tool_result",
                            data={
                                "tool_id": block.tool_use_id,
                                "output": block.content,
                                "is_error": block.is_error,
                                "parent_tool_use_id": message.parent_tool_use_id,
                            },
                        ))
                    elif isinstance(block, TextBlock):
                        events.append(StreamingEvent(
                            event_type="user_message",
                            data={
                                "type": "text",
                                "text": block.text,
                                "parent_tool_use_id": message.parent_tool_use_id,
                            },
                        ))
            else:
                # String content
                events.append(StreamingEvent(
                    event_type="user_message",
                    data={
                        "type": "text",
                        "text": content,
                        "parent_tool_use_id": message.parent_tool_use_id,
                    },
                ))

        return events

    async def send_message_streaming(
        self,
        content_stream: AsyncIterator[Dict[str, Any]],
        message_id: str,
    ) -> AsyncIterator[StreamingEvent]:
        """
        Send a message with streaming input.

        Args:
            content_stream: Async iterator yielding {"type": "text", "text": "chunk..."}
            message_id: Unique identifier for this message exchange

        Yields:
            StreamingEvent objects containing response chunks
        """
        if not self.client or not self._is_connected:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        try:
            await self.client.query(content_stream, session_id=self.session_id or "default")

            async for message in self.client.receive_response():
                events = self._process_message(message)
                for event in events:
                    logger.info(f"[CLAUDE_AGENT] Yielding event (streaming): type={event.event_type}, session_id={event.session_id}")
                    logger.debug(f"[CLAUDE_AGENT] Event data (streaming): {event.data}")
                    yield event

                if isinstance(message, ResultMessage):
                    self.session_id = message.session_id

                    # Cache session_id for future resume
                    if self.session_cache and self.session_id:
                        await self.session_cache.set_session_id(
                            self.conversation_id,
                            self.session_id
                        )

                    result_event = StreamingEvent(
                        event_type="result",
                        data={
                            "message_id": message_id,
                            "duration_ms": message.duration_ms,
                            "num_turns": message.num_turns,
                            "is_error": message.is_error,
                            "result": message.result,
                        },
                        session_id=self.session_id,
                    )
                    logger.info(f"[CLAUDE_AGENT] Yielding result event (streaming): session_id={self.session_id}, num_turns={message.num_turns}, duration_ms={message.duration_ms}")
                    logger.debug(f"[CLAUDE_AGENT] Result data (streaming): {result_event.data}")
                    yield result_event

        except Exception as e:
            logger.error(f"[CLAUDE_AGENT] Error in streaming message: {e}")
            error_event = StreamingEvent(
                event_type="error",
                data={
                    "message_id": message_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            logger.error(f"[CLAUDE_AGENT] Yielding error event (streaming): {error_event.data}")
            yield error_event
            raise

    async def interrupt(self) -> None:
        """Interrupt the current response generation."""
        if self.client and self._is_connected:
            await self.client.interrupt()

    async def disconnect(self) -> None:
        """Disconnect and cleanup the client and workspace."""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.warning(f"[CLAUDE_AGENT] Error disconnecting client: {e}")
            finally:
                self._is_connected = False
                self.client = None

        # Note: We don't cleanup workspace here as it may be needed
        # for conversation resume. Cleanup happens on conversation archive.

    def cleanup_workspace(self) -> None:
        """Explicitly cleanup the workspace (call on conversation archive)."""
        if self.workspace_manager:
            self.workspace_manager.cleanup()

    async def __aenter__(self) -> "ConversationAgentManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


async def process_single_message(
    content: str,
    message_id: str,
    project_id: str,
    conversation_id: str,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    agent_config: Optional[AgentConfig] = None,
    session_cache: Optional[SessionCache] = None,
) -> AsyncIterator[StreamingEvent]:
    """
    Process a single message and stream the response.

    This creates a client per message with resume capability.
    Best for typical request/response pattern where messages
    may be processed by different service instances.

    Args:
        content: The user message content
        message_id: Unique identifier for this message
        project_id: Project ID for context
        conversation_id: Conversation ID
        agent_id: Optional agent ID for tracking
        session_id: Optional session ID to resume
        agent_config: Optional agent configuration
        session_cache: Optional session cache for resume

    Yields:
        StreamingEvent objects containing response chunks
    """
    manager = ConversationAgentManager(
        project_id=project_id,
        conversation_id=conversation_id,
        agent_id=agent_id,
        agent_config=agent_config,
        session_cache=session_cache,
    )

    try:
        await manager.initialize(session_id=session_id)

        async for event in manager.send_message(content, message_id):
            yield event

    finally:
        await manager.disconnect()

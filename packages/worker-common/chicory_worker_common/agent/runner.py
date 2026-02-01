"""
Claude Agent Runner - Pure Claude SDK workflow orchestration.

Replaces LangGraph StateGraph with native Claude SDK patterns.
Provides the same interface (astream) for compatibility with existing code.
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Union

# Optional: Claude Agent SDK imports
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        ThinkingBlock,
        ToolResultBlock,
        ToolUseBlock,
        UserMessage,
        query,
    )
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    query = None
    ClaudeAgentOptions = None
    AssistantMessage = None
    ResultMessage = None
    TextBlock = None
    ThinkingBlock = None
    ToolResultBlock = None
    ToolUseBlock = None
    UserMessage = None

logger = logging.getLogger(__name__)

# Constants
DEFAULT_ERROR_MESSAGE = (
    "I'm sorry, but something went wrong while processing your request. "
    "Please try again or contact support if the issue persists."
)
TASK_CANCELLED_MESSAGE = "Task was cancelled by user."


@dataclass
class AgentRunConfig:
    """Configuration for agent execution."""

    project_id: str
    agent_id: str
    mcp_config: Dict[str, Any] = field(default_factory=dict)
    max_turns: int = 100
    model: str = "claude-sonnet-4-20250514"
    working_directory: Optional[str] = None
    context_directory: Optional[str] = None
    env_variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    """Result of agent execution."""

    generation: str
    messages: List[Any]
    usage: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False
    is_error: bool = False
    duration_ms: float = 0


class ClaudeAgentRunner:
    """
    Pure Claude SDK agent runner.

    Replaces LangGraph StateGraph orchestration with direct Claude SDK calls.
    Maintains interface compatibility for easy migration.

    Usage:
        config = AgentRunConfig(project_id="proj", agent_id="agent")
        runner = ClaudeAgentRunner(config)
        await runner.initialize(options)

        # Single run
        result = await runner.run("What is 2+2?")

        # Streaming (LangGraph-compatible interface)
        async for event in runner.astream({"question": "..."}, config):
            print(event)
    """

    def __init__(self, config: AgentRunConfig):
        """Initialize the runner with configuration."""
        self.config = config
        self._options: Optional[ClaudeAgentOptions] = None
        self._cancellation_check: Optional[Callable[[], Awaitable[bool]]] = None
        self._last_cancel_check: float = 0
        self._cancel_check_interval: float = 5.0  # Check every 5 seconds
        self._runtime_config: Dict[str, Any] = {}
        self._messages: List[Any] = []  # Collected messages for audit trail

    @property
    def is_initialized(self) -> bool:
        """Check if runner is initialized with options."""
        return self._options is not None

    async def initialize(self, options: ClaudeAgentOptions) -> None:
        """
        Initialize with pre-built options.

        Args:
            options: ClaudeAgentOptions built via AgentOptionsBuilder or manually.
        """
        if not CLAUDE_SDK_AVAILABLE:
            raise ImportError(
                "claude-agent-sdk is required. Install with: pip install claude-agent-sdk"
            )
        self._options = options
        logger.info(f"ClaudeAgentRunner initialized for agent {self.config.agent_id}")

    def _inject_env_variables(self, options: ClaudeAgentOptions) -> ClaudeAgentOptions:
        """Inject environment variables into options settings."""
        env_vars = self.config.env_variables.copy()

        # Also get from runtime config if available
        runtime_env = self._runtime_config.get("configurable", {}).get("env_variables", {})
        env_vars.update(runtime_env)

        if not env_vars:
            return options

        try:
            existing_settings = json.loads(options.settings) if options.settings else {}
            existing_env = existing_settings.get("env", {})
            existing_env.update(env_vars)
            existing_settings["env"] = existing_env
            options.settings = json.dumps(existing_settings)
            logger.info(f"Injected {len(env_vars)} environment variables")
        except Exception as e:
            logger.warning(f"Failed to inject env variables: {e}")

        return options

    async def run(
        self,
        question: str,
        context: str = "",
        output_format: str = "",
        cancellation_check: Optional[Callable[[], Awaitable[bool]]] = None,
        max_retries: int = 3,
    ) -> AgentRunResult:
        """
        Execute agent and return result.

        Args:
            question: The user's question/prompt.
            context: Additional context to include.
            output_format: Expected output format (e.g., "json", "markdown").
            cancellation_check: Async callable that returns True if cancelled.
            max_retries: Number of retries on failure.

        Returns:
            AgentRunResult with generation and messages.
        """
        if not self.is_initialized:
            raise RuntimeError("Runner not initialized. Call initialize() first.")

        self._cancellation_check = cancellation_check
        self._last_cancel_check = 0

        # Build the full prompt
        user_prompt = self._build_prompt(question, context, output_format)

        # Execute with retry
        result, messages = await self._invoke_with_retry(user_prompt, max_retries)

        is_cancelled = result == TASK_CANCELLED_MESSAGE
        is_error = result == DEFAULT_ERROR_MESSAGE or "something went wrong" in result.lower()

        return AgentRunResult(
            generation=result,
            messages=messages,
            cancelled=is_cancelled,
            is_error=is_error,
        )

    def _build_prompt(
        self,
        question: str,
        context: str = "",
        output_format: str = "",
    ) -> str:
        """Build the full prompt for the agent."""
        parts = []

        if context:
            parts.append(f"## Context\n{context}\n")

        parts.append(f"## Question\n{question}")

        if output_format:
            parts.append(f"\n## Expected Output Format\n{output_format}")

        return "\n".join(parts)

    async def _invoke_with_retry(
        self,
        user_prompt: str,
        max_retries: int = 3,
    ) -> tuple[str, List[Any]]:
        """Invoke agent with automatic retry on failure."""
        last_error = None
        all_messages = []

        for attempt in range(1, max_retries + 1):
            current_prompt = user_prompt

            if last_error and attempt > 1:
                current_prompt = f"""[RETRY ATTEMPT {attempt}/{max_retries}]
The previous attempt failed with the following error:
---
{last_error}
---
Please try a different approach. Consider:
- Process data in smaller chunks if memory error
- Use alternative methods if a tool failed
- Verify file paths and try again

Original request: {user_prompt}
"""
                logger.info(f"Retry attempt {attempt}/{max_retries}")

            result, messages = await self._invoke(current_prompt)
            all_messages.extend(messages)

            # Don't retry on cancellation
            if result == TASK_CANCELLED_MESSAGE:
                return result, messages

            # Check for errors that should trigger retry
            is_error = result and (
                result == DEFAULT_ERROR_MESSAGE
                or "something went wrong" in result.lower()
                or "execution failed" in result.lower()
            )

            if is_error:
                last_error = result
                logger.warning(f"Attempt {attempt}/{max_retries} failed: {result[:200]}...")
                if attempt < max_retries:
                    continue
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    return result, all_messages

            # Success
            logger.info(f"Completed on attempt {attempt}/{max_retries}")
            return result, messages

        return DEFAULT_ERROR_MESSAGE, all_messages

    async def _invoke(self, user_prompt: str) -> tuple[str, List[Any]]:
        """Single invocation of the Claude agent."""
        start_time = time.time()
        final_result = ""
        messages = []
        message_count = 0
        tool_count = 0

        # Inject env variables
        options = self._inject_env_variables(self._options)

        try:
            query_gen = query(prompt=user_prompt, options=options)

            async for message in query_gen:
                # Check for cancellation periodically
                current_time = time.time()
                if self._cancellation_check and (
                    current_time - self._last_cancel_check
                ) >= self._cancel_check_interval:
                    self._last_cancel_check = current_time
                    try:
                        is_cancelled = await self._cancellation_check()
                        if is_cancelled:
                            logger.info("Task cancelled - aborting execution")
                            try:
                                await query_gen.aclose()
                            except Exception:
                                pass
                            return TASK_CANCELLED_MESSAGE, messages
                    except Exception as e:
                        logger.warning(f"Error checking cancellation: {e}")

                message_count += 1
                messages.append(message)
                elapsed = time.time() - start_time
                logger.debug(f"Message #{message_count} ({type(message).__name__}) at {elapsed:.2f}s")

                # Process message to extract final result
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            final_result = block.text
                        elif isinstance(block, ToolUseBlock):
                            tool_count += 1
                            logger.debug(f"Tool: {block.name}")

                elif isinstance(message, ResultMessage):
                    if message.result:
                        final_result = message.result
                    logger.info(
                        f"Query completed: {message_count} messages, "
                        f"{tool_count} tools, {message.duration_ms}ms"
                    )

            return final_result or DEFAULT_ERROR_MESSAGE, messages

        except Exception as e:
            logger.error(f"Error in Claude agent invocation: {e}", exc_info=True)
            return DEFAULT_ERROR_MESSAGE, messages

    async def astream(
        self,
        input_dict: Dict[str, Any],
        config: Dict[str, Any],
        cancellation_check: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream agent execution - LangGraph-compatible interface.

        This provides the same interface as LangGraph's workflow.astream()
        for easy migration. Yields dictionaries in the format:
        {"agent_node": {"generation": str, "messages": list}}

        Args:
            input_dict: Input with keys: question, context, output_format
            config: Runtime config with configurable settings
            cancellation_check: Optional cancellation callback

        Yields:
            Dictionaries matching LangGraph output format
        """
        if not self.is_initialized:
            raise RuntimeError("Runner not initialized. Call initialize() first.")

        self._runtime_config = config
        self._cancellation_check = cancellation_check
        self._last_cancel_check = 0

        # Extract inputs
        question = input_dict.get("question", "")
        context = input_dict.get("context", "")
        output_format = input_dict.get("output_format", "")

        # Build prompt
        user_prompt = self._build_prompt(question, context, output_format)

        # Stream execution
        async for event in self._stream_invoke(user_prompt):
            yield event

    async def _stream_invoke(self, user_prompt: str) -> AsyncIterator[Dict[str, Any]]:
        """Internal streaming invocation."""
        final_result = ""
        messages = []
        options = self._inject_env_variables(self._options)

        try:
            query_gen = query(prompt=user_prompt, options=options)

            async for message in query_gen:
                # Check cancellation
                current_time = time.time()
                if self._cancellation_check and (
                    current_time - self._last_cancel_check
                ) >= self._cancel_check_interval:
                    self._last_cancel_check = current_time
                    try:
                        is_cancelled = await self._cancellation_check()
                        if is_cancelled:
                            logger.info("Task cancelled")
                            try:
                                await query_gen.aclose()
                            except Exception:
                                pass
                            yield {
                                "agent_node": {
                                    "generation": TASK_CANCELLED_MESSAGE,
                                    "messages": messages,
                                }
                            }
                            return
                    except Exception as e:
                        logger.warning(f"Cancellation check error: {e}")

                messages.append(message)

                # Extract text from messages
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            final_result = block.text

                elif isinstance(message, ResultMessage):
                    if message.result:
                        final_result = message.result

            # Yield final result in LangGraph format
            yield {
                "agent_node": {
                    "generation": final_result or DEFAULT_ERROR_MESSAGE,
                    "messages": messages,
                }
            }

        except Exception as e:
            logger.error(f"Error in streaming invocation: {e}", exc_info=True)
            yield {
                "agent_node": {
                    "generation": DEFAULT_ERROR_MESSAGE,
                    "messages": messages,
                }
            }

    @property
    def collected_messages(self) -> List[Any]:
        """Get all messages collected during execution."""
        return self._messages

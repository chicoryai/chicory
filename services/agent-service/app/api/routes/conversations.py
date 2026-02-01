import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import (
    SendMessageRequest,
    InterruptRequest,
    MessageResponse,
)
from app.services.claude_agent import (
    ConversationAgentManager,
    process_single_message,
    StreamingEvent,
)
from app.services.redis_client import get_redis_client
from app.services.session_cache import SessionCache

logger = logging.getLogger(__name__)

router = APIRouter()

# Track active managers for interrupt capability
_active_managers: dict[str, ConversationAgentManager] = {}


async def _generate_sse_events(
    events: AsyncIterator[StreamingEvent],
    message_id: str,
    conversation_id: str,
) -> AsyncIterator[dict]:
    """Convert streaming events to SSE format."""
    try:
        async for event in events:
            yield {
                "event": event.event_type,
                "data": json.dumps({
                    **event.data,
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "session_id": event.session_id,
                }),
            }
    except Exception as e:
        logger.error(f"Error streaming message {message_id}: {e}")
        yield {
            "event": "error",
            "data": json.dumps({
                "message_id": message_id,
                "conversation_id": conversation_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }),
        }


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
):
    """
    Send a message and stream the response via SSE.

    This endpoint accepts a message, processes it through the Claude Agent SDK,
    and streams the response back as Server-Sent Events.

    Events emitted:
    - message_chunk: Text content from the assistant
    - tool_use: When a tool is invoked
    - tool_result: Results from tool execution
    - result: Final result with session_id and metrics
    - error: If an error occurs

    The session_id returned in the result event should be stored
    to resume the conversation in subsequent messages.
    """
    print(f"[AGENT-SERVICE] ========== SEND_MESSAGE ENDPOINT CALLED ==========")
    print(f"[AGENT-SERVICE] conversation_id={conversation_id}")
    print(f"[AGENT-SERVICE] message_id={request.message_id}")
    print(f"[AGENT-SERVICE] project_id={request.project_id}")
    print(f"[AGENT-SERVICE] agent_id={request.agent_id or 'None (project-scoped)'}")
    print(f"[AGENT-SERVICE] session_id={request.session_id}")
    print(f"[AGENT-SERVICE] content_length={len(request.content)}")
    print(f"[AGENT-SERVICE] content_preview={request.content[:100]}..." if len(request.content) > 100 else f"[AGENT-SERVICE] content={request.content}")
    print(f"[AGENT-SERVICE] agent_config={request.agent_config}")

    logger.info(f"[AGENT-SERVICE] Received message request for conversation {conversation_id}")

    # Get Redis client and session cache
    print(f"[AGENT-SERVICE] Getting Redis client for session cache...")
    redis_client = await get_redis_client()
    session_cache = SessionCache(redis_client)

    print(f"[AGENT-SERVICE] Creating ConversationAgentManager with session cache...")
    manager = ConversationAgentManager(
        project_id=request.project_id,
        conversation_id=conversation_id,
        agent_id=request.agent_id,  # Optional
        agent_config=request.agent_config,
        session_cache=session_cache,
    )
    print(f"[AGENT-SERVICE] Manager created")

    # Track for potential interrupt
    manager_key = f"{conversation_id}:{request.message_id}"
    _active_managers[manager_key] = manager
    print(f"[AGENT-SERVICE] Manager registered with key: {manager_key}")

    async def generate_response():
        print(f"[AGENT-SERVICE] ========== GENERATE_RESPONSE START ==========")
        try:
            print(f"[AGENT-SERVICE] Initializing manager with session_id={request.session_id}...")
            await manager.initialize(session_id=request.session_id)
            print(f"[AGENT-SERVICE] Manager initialized successfully")

            print(f"[AGENT-SERVICE] Calling manager.send_message()...")
            events = manager.send_message(
                content=request.content,
                message_id=request.message_id,
            )
            print(f"[AGENT-SERVICE] send_message returned, iterating events...")

            event_count = 0
            async for sse_event in _generate_sse_events(
                events,
                request.message_id,
                conversation_id,
            ):
                event_count += 1
                print(f"[AGENT-SERVICE] Yielding SSE event #{event_count}: {sse_event.get('event', 'unknown')}")
                yield sse_event

            print(f"[AGENT-SERVICE] All events yielded, total={event_count}")

        except Exception as e:
            print(f"[AGENT-SERVICE] ERROR in generate_response: {type(e).__name__}: {e}")
            logger.error(f"Error processing message {request.message_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "message_id": request.message_id,
                    "conversation_id": conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }),
            }
        finally:
            print(f"[AGENT-SERVICE] Cleaning up manager...")
            # Cleanup
            _active_managers.pop(manager_key, None)
            await manager.disconnect()
            print(f"[AGENT-SERVICE] ========== GENERATE_RESPONSE END ==========")

    print(f"[AGENT-SERVICE] Returning EventSourceResponse...")
    return EventSourceResponse(generate_response())


@router.post("/{conversation_id}/messages/stream")
async def send_message_streaming(
    conversation_id: str,
    request: SendMessageRequest,
):
    """
    Send a message with streaming input.

    This endpoint is designed for progressive input building,
    such as real-time typing from websocket connections or
    large document uploads processed in chunks.

    For standard single-message requests, use POST /messages instead.
    """
    # For now, treat as regular message
    # Full streaming input would require websocket or chunked transfer
    return await send_message(conversation_id, request)


@router.post("/{conversation_id}/interrupt")
async def interrupt_response(
    conversation_id: str,
    request: InterruptRequest,
):
    """
    Interrupt an active response generation.

    This stops the Claude agent from continuing to generate
    the current response. The partial response up to the
    interrupt point will be preserved.
    """
    manager_key = f"{conversation_id}:{request.message_id}"
    manager = _active_managers.get(manager_key)

    if not manager:
        raise HTTPException(
            status_code=404,
            detail=f"No active response found for message {request.message_id}",
        )

    try:
        await manager.interrupt()
        return MessageResponse(
            message_id=request.message_id,
            status="interrupted",
        )
    except Exception as e:
        logger.error(f"Error interrupting message {request.message_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to interrupt: {str(e)}",
        )


@router.delete("/{conversation_id}/session")
async def disconnect_session(
    conversation_id: str,
):
    """
    Force disconnect all active sessions for a conversation.

    This is useful for cleanup when a conversation is archived
    or when the user explicitly wants to end all sessions.
    Also clears the cached session from Redis.
    """
    # Find and disconnect all managers for this conversation
    keys_to_remove = [
        key for key in _active_managers.keys()
        if key.startswith(f"{conversation_id}:")
    ]

    disconnected = 0
    for key in keys_to_remove:
        manager = _active_managers.pop(key, None)
        if manager:
            try:
                await manager.disconnect()
                disconnected += 1
            except Exception as e:
                logger.warning(f"Error disconnecting session {key}: {e}")

    # Clear cached session from Redis
    try:
        redis_client = await get_redis_client()
        session_cache = SessionCache(redis_client)
        await session_cache.delete(conversation_id)
        logger.info(f"Cleared session cache for conversation {conversation_id}")
    except Exception as e:
        logger.warning(f"Error clearing session cache for {conversation_id}: {e}")

    return {
        "conversation_id": conversation_id,
        "sessions_disconnected": disconnected,
    }


@router.get("/sessions")
async def list_active_sessions():
    """
    List all active sessions (admin endpoint).

    Returns information about currently active conversation managers.
    """
    sessions = []
    for key, manager in _active_managers.items():
        conversation_id, message_id = key.split(":", 1)
        sessions.append({
            "conversation_id": conversation_id,
            "message_id": message_id,
            "project_id": manager.project_id,
            "agent_id": manager.agent_id,
            "session_id": manager.session_id,
            "is_connected": manager._is_connected,
        })

    return {
        "sessions": sessions,
        "total": len(sessions),
    }

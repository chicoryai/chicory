from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse
from beanie.odm.queries.update import UpdateResponse
import json
import asyncio
import logging
from datetime import datetime
import os
import httpx

logger = logging.getLogger(__name__)

from app.models.project import Project
from app.models.conversation import (
    Conversation,
    ConversationCreate,
    ConversationResponse,
    ConversationList,
    ConversationUpdate,
    ConversationStatus,
)
from app.models.message import (
    Message,
    MessageCreate,
    MessageResponse,
    MessageList,
    MessageRole,
    MessageStatus,
    MessageChunk,
    MessageComplete,
    SendMessageRequest,
)

router = APIRouter()

# Agent service URL
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8083")


# ============================================================================
# Conversation Endpoints
# ============================================================================

@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationResponse,
    status_code=201
)
async def create_conversation(
    project_id: str,
    conversation_data: ConversationCreate
):
    """Create a new conversation for a project"""
    # Validate project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create the conversation
    conversation = Conversation(
        project_id=project_id,
        name=conversation_data.name,
        status=ConversationStatus.ACTIVE,
        message_count=0,
        metadata=conversation_data.metadata or {},
    )
    await conversation.save()

    return ConversationResponse(
        id=str(conversation.id),
        project_id=conversation.project_id,
        name=conversation.name,
        status=conversation.status.value,
        message_count=conversation.message_count,
        session_id=conversation.session_id,
        metadata=conversation.metadata,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get(
    "/projects/{project_id}/conversations",
    response_model=ConversationList
)
async def list_conversations(
    project_id: str,
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status (active, archived)"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """List conversations for a project"""
    # Validate project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build query
    query = {"project_id": project_id}
    if status:
        query["status"] = status

    # Execute query with pagination
    sort_direction = 1 if sort_order.lower() == "asc" else -1
    conversations = await (
        Conversation.find(query)
        .sort([("created_at", sort_direction)])
        .skip(skip)
        .limit(limit + 1)
        .to_list()
    )

    # Check for more results
    has_more = len(conversations) > limit
    if has_more:
        conversations = conversations[:limit]

    # Get total count
    total = await Conversation.find(query).count()

    return ConversationList(
        conversations=[
            ConversationResponse(
                id=str(conv.id),
                project_id=conv.project_id,
                name=conv.name,
                status=conv.status.value,
                message_count=conv.message_count,
                session_id=conv.session_id,
                metadata=conv.metadata,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv in conversations
        ],
        has_more=has_more,
        total=total,
    )


@router.get(
    "/projects/{project_id}/conversations/{conversation_id}",
    response_model=ConversationResponse
)
async def get_conversation(project_id: str, conversation_id: str):
    """Get a specific conversation"""
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    return ConversationResponse(
        id=str(conversation.id),
        project_id=conversation.project_id,
        name=conversation.name,
        status=conversation.status.value,
        message_count=conversation.message_count,
        session_id=conversation.session_id,
        metadata=conversation.metadata,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.patch(
    "/projects/{project_id}/conversations/{conversation_id}",
    response_model=ConversationResponse
)
async def update_conversation(
    project_id: str,
    conversation_id: str,
    update_data: ConversationUpdate
):
    """Update a conversation (name, status, metadata)"""
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    # Build update dict
    updates = {"updated_at": datetime.utcnow()}
    if update_data.name is not None:
        updates["name"] = update_data.name
    if update_data.status is not None:
        updates["status"] = update_data.status
    if update_data.metadata is not None:
        updates["metadata"] = update_data.metadata

    await conversation.update({"$set": updates})

    # Refresh conversation
    conversation = await Conversation.get(conversation_id)

    return ConversationResponse(
        id=str(conversation.id),
        project_id=conversation.project_id,
        name=conversation.name,
        status=conversation.status.value,
        message_count=conversation.message_count,
        session_id=conversation.session_id,
        metadata=conversation.metadata,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.delete(
    "/projects/{project_id}/conversations/{conversation_id}"
)
async def archive_conversation(project_id: str, conversation_id: str):
    """Archive a conversation (soft delete)"""
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    # Archive (soft delete)
    await conversation.update({
        "$set": {
            "status": ConversationStatus.ARCHIVED,
            "updated_at": datetime.utcnow(),
        }
    })

    return {"message": "Conversation archived successfully"}


# ============================================================================
# Message Endpoints
# ============================================================================

@router.post(
    "/projects/{project_id}/conversations/{conversation_id}/messages",
    response_model=Dict[str, Any],
    status_code=201
)
async def send_message(
    project_id: str,
    conversation_id: str,
    message_data: SendMessageRequest
):
    """
    Send a message to a conversation.

    Creates both user and assistant messages, then triggers the agent-service
    to process the message. Returns both message IDs for streaming.
    """
    # Validate conversation exists and belongs to project
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    if conversation.status == ConversationStatus.ARCHIVED:
        raise HTTPException(
            status_code=400,
            detail="Cannot send messages to archived conversation"
        )

    # Atomically increment message_count and get the new value for turn calculation
    # This prevents race conditions when multiple messages are sent concurrently
    updated_conversation = await Conversation.find_one(
        {"_id": conversation_id}
    ).update(
        {"$inc": {"message_count": 2}, "$set": {"updated_at": datetime.utcnow()}},
        response_type=UpdateResponse.NEW_DOCUMENT
    )

    # Calculate turn number from the updated count (after increment)
    # Since we incremented by 2, the turn number is (new_count - 2) // 2 + 1 = (new_count // 2)
    turn_number = (updated_conversation.message_count) // 2

    # Create user message with content_blocks
    user_message = Message(
        conversation_id=conversation_id,
        project_id=project_id,
        role=MessageRole.USER,
        content_blocks=[{"type": "text", "text": message_data.content}],
        status=MessageStatus.COMPLETED,
        turn_number=turn_number,
        metadata=message_data.metadata or {},
        completed_at=datetime.utcnow(),
    )
    await user_message.save()

    # Create assistant message (pending, to be filled by agent-service)
    assistant_message = Message(
        conversation_id=conversation_id,
        project_id=project_id,
        role=MessageRole.ASSISTANT,
        content_blocks=[],
        status=MessageStatus.PENDING,
        parent_message_id=str(user_message.id),
        turn_number=turn_number,
        metadata={},
    )
    await assistant_message.save()

    return {
        "user_message_id": str(user_message.id),
        "assistant_message_id": str(assistant_message.id),
        "conversation_id": conversation_id,
        "turn_number": turn_number,
    }


@router.get(
    "/projects/{project_id}/conversations/{conversation_id}/messages",
    response_model=MessageList
)
async def list_messages(
    project_id: str,
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
):
    """List messages in a conversation"""
    # Validate conversation exists
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    # Query messages
    sort_direction = 1 if sort_order.lower() == "asc" else -1
    messages = await (
        Message.find({"conversation_id": conversation_id})
        .sort([("created_at", sort_direction)])
        .skip(skip)
        .limit(limit + 1)
        .to_list()
    )

    # Check for more results
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    # Get total count
    total = await Message.find({"conversation_id": conversation_id}).count()

    return MessageList(
        messages=[
            MessageResponse(
                id=str(msg.id),
                conversation_id=msg.conversation_id,
                project_id=msg.project_id,
                role=msg.role.value,
                content_blocks=msg.content_blocks,
                status=msg.status.value if msg.status else None,
                parent_message_id=msg.parent_message_id,
                turn_number=msg.turn_number,
                metadata=msg.metadata,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
                completed_at=msg.completed_at,
            )
            for msg in messages
        ],
        has_more=has_more,
        total=total,
    )


@router.get(
    "/projects/{project_id}/conversations/{conversation_id}/messages/{message_id}",
    response_model=MessageResponse
)
async def get_message(
    project_id: str,
    conversation_id: str,
    message_id: str
):
    """Get a specific message"""
    message = await Message.get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.conversation_id != conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Message does not belong to the specified conversation"
        )

    # Validate conversation belongs to project
    conversation = await Conversation.get(conversation_id)
    if not conversation or conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    return MessageResponse(
        id=str(message.id),
        conversation_id=message.conversation_id,
        project_id=message.project_id,
        role=message.role.value,
        content_blocks=message.content_blocks,
        status=message.status.value if message.status else None,
        parent_message_id=message.parent_message_id,
        turn_number=message.turn_number,
        metadata=message.metadata,
        created_at=message.created_at,
        updated_at=message.updated_at,
        completed_at=message.completed_at,
    )


@router.get(
    "/projects/{project_id}/conversations/{conversation_id}/messages/{message_id}/stream"
)
async def stream_message(
    request: Request,
    project_id: str,
    conversation_id: str,
    message_id: str
):
    """
    Stream the response for a message via SSE.

    This endpoint proxies SSE events from the agent-service and updates
    the message content as chunks arrive.
    """
    logger.debug(f"stream_message called: conversation_id={conversation_id}, message_id={message_id}")

    # Validate message exists and is an assistant message
    message = await Message.get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.role != MessageRole.ASSISTANT:
        raise HTTPException(
            status_code=400,
            detail="Only assistant messages can be streamed"
        )

    if message.conversation_id != conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Message does not belong to the specified conversation"
        )

    # Get conversation and validate
    conversation = await Conversation.get(conversation_id)
    if not conversation or conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    # Get the parent user message content
    user_message = await Message.get(message.parent_message_id) if message.parent_message_id else None
    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Parent user message not found"
        )
    # Extract text content from user message content_blocks
    user_content = ""
    for block in user_message.content_blocks:
        if block.get("type") == "text":
            user_content += block.get("text", "")

    async def event_generator():
        """Generate SSE events by proxying from agent-service"""
        # Initial connection event
        yield {
            "event": "message_start",
            "data": json.dumps({
                "id": message_id,
                "conversation_id": conversation_id,
                "role": "assistant",
            })
        }

        # Update message status to processing
        await message.update({
            "$set": {
                "status": MessageStatus.PROCESSING,
                "updated_at": datetime.utcnow(),
            }
        })

        # Track content blocks for fused persistence
        content_blocks = []
        session_id = None
        last_persist_time = None

        async def persist_content_blocks():
            """Persist current content_blocks to database"""
            nonlocal last_persist_time
            await message.update({
                "$set": {
                    "content_blocks": content_blocks,
                    "updated_at": datetime.utcnow(),
                }
            })
            last_persist_time = datetime.utcnow()

        try:
            # Call agent-service to process the message
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
                # Build agent config with workspace path
                # Agent-service will create the workspace at this path on persistent volume
                working_directory = f"/data/workspaces/{project_id}/{conversation_id}/work_dir"

                agent_config = {
                    "max_turns": 15,
                    "working_directory": working_directory,
                }

                agent_request = {
                    "content": user_content,
                    "message_id": message_id,
                    "project_id": project_id,
                    "session_id": conversation.session_id,
                    "agent_config": agent_config,
                }

                agent_url = f"{AGENT_SERVICE_URL}/conversations/{conversation_id}/messages"
                logger.debug(f"Calling agent service: {agent_url}")

                async with client.stream(
                    "POST",
                    agent_url,
                    json=agent_request,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Agent service error: {error_text.decode()}"
                        )

                    # Parse SSE stream from agent-service
                    async for line in response.aiter_lines():
                        if await request.is_disconnected():
                            break

                        if not line:
                            continue

                        # Parse SSE format
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("data:"):
                            data_str = line[5:].strip()
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            # Process different event types
                            # Build content_blocks for persistence while yielding events individually
                            if event_type == "message_chunk":
                                text = data.get("text", "")

                                # Fuse consecutive text blocks for persistence
                                if content_blocks and content_blocks[-1].get("type") == "text":
                                    content_blocks[-1]["text"] += text
                                else:
                                    content_blocks.append({"type": "text", "text": text})

                                # Persist with 1-second debounce
                                if last_persist_time is None or (datetime.utcnow() - last_persist_time).total_seconds() >= 1.0:
                                    await persist_content_blocks()

                                # Forward to client (yield individual event for real-time UI)
                                yield {
                                    "event": "message_chunk",
                                    "data": json.dumps({
                                        "id": message_id,
                                        "content_chunk": text,
                                    })
                                }

                            elif event_type == "thinking":
                                # Add thinking block for persistence
                                content_blocks.append({
                                    "type": "thinking",
                                    "thinking": data.get("thinking", ""),
                                    "signature": data.get("signature", ""),
                                })

                                # Persist immediately
                                await persist_content_blocks()

                                # Forward to client
                                yield {
                                    "event": "thinking",
                                    "data": json.dumps(data)
                                }

                            elif event_type == "tool_use":
                                # Add tool_use block with output=None (will be fused with tool_result)
                                content_blocks.append({
                                    "type": "tool_use",
                                    "id": data.get("tool_id"),
                                    "name": data.get("tool_name"),
                                    "input": data.get("input", {}),
                                    "output": None,
                                    "is_error": False,
                                    "active_description": data.get("active_description"),
                                })

                                # Forward to client (yield separate event for real-time progress)
                                yield {
                                    "event": "tool_use",
                                    "data": json.dumps(data)
                                }

                            elif event_type == "tool_result":
                                # FUSE: Find matching tool_use block and update its output
                                tool_id = data.get("tool_id")
                                for block in content_blocks:
                                    if block.get("type") == "tool_use" and block.get("id") == tool_id:
                                        block["output"] = data.get("output")
                                        block["is_error"] = data.get("is_error", False)
                                        break

                                # Persist immediately (tool_use now complete with result)
                                await persist_content_blocks()

                                # Forward to client (yield separate event for real-time progress)
                                yield {
                                    "event": "tool_result",
                                    "data": json.dumps(data)
                                }

                            elif event_type == "result":
                                session_id = data.get("session_id")

                                # Store result data in metadata
                                result_metadata = {
                                    "duration_ms": data.get("duration_ms"),
                                    "num_turns": data.get("num_turns"),
                                    "is_error": data.get("is_error"),
                                    "result": data.get("result"),
                                }

                                # PERSIST: Save fused content_blocks to database
                                await message.update({
                                    "$set": {
                                        "content_blocks": content_blocks,
                                        "status": MessageStatus.COMPLETED,
                                        "metadata": {**message.metadata, **result_metadata},
                                        "completed_at": datetime.utcnow(),
                                        "updated_at": datetime.utcnow(),
                                    }
                                })

                                # Update conversation session_id
                                if session_id:
                                    await conversation.update({
                                        "$set": {
                                            "session_id": session_id,
                                            "last_session_id": conversation.session_id,
                                            "updated_at": datetime.utcnow(),
                                        }
                                    })

                                yield {
                                    "event": "message_complete",
                                    "data": json.dumps({
                                        "id": message_id,
                                        "session_id": session_id,
                                        "completed_at": datetime.utcnow().isoformat(),
                                    })
                                }

                            elif event_type == "error":
                                # Mark message as failed
                                await message.update({
                                    "$set": {
                                        "status": MessageStatus.FAILED,
                                        "metadata": {
                                            **message.metadata,
                                            "error": data.get("error"),
                                        },
                                        "updated_at": datetime.utcnow(),
                                    }
                                })

                                yield {
                                    "event": "error",
                                    "data": json.dumps(data)
                                }

        except httpx.RequestError as e:
            # Handle connection errors to agent-service
            await message.update({
                "$set": {
                    "status": MessageStatus.FAILED,
                    "metadata": {
                        **message.metadata,
                        "error": f"Agent service connection error: {str(e)}",
                    },
                    "updated_at": datetime.utcnow(),
                }
            })

            yield {
                "event": "error",
                "data": json.dumps({
                    "message_id": message_id,
                    "error": f"Agent service connection error: {str(e)}",
                    "error_type": "ConnectionError",
                })
            }

        except Exception as e:
            # Handle unexpected errors
            await message.update({
                "$set": {
                    "status": MessageStatus.FAILED,
                    "metadata": {
                        **message.metadata,
                        "error": str(e),
                    },
                    "updated_at": datetime.utcnow(),
                }
            })

            yield {
                "event": "error",
                "data": json.dumps({
                    "message_id": message_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                })
            }

    return EventSourceResponse(event_generator())


@router.post(
    "/projects/{project_id}/conversations/{conversation_id}/messages/{message_id}/cancel"
)
async def cancel_message(
    project_id: str,
    conversation_id: str,
    message_id: str
):
    """Cancel a message that is pending or processing"""
    # Validate message exists
    message = await Message.get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.conversation_id != conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Message does not belong to the specified conversation"
        )

    # Validate conversation belongs to project
    conversation = await Conversation.get(conversation_id)
    if not conversation or conversation.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation does not belong to the specified project"
        )

    # Check if message can be cancelled
    if message.status not in [MessageStatus.PENDING, MessageStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel message with status '{message.status.value}'"
        )

    # Try to interrupt at agent-service
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            await client.post(
                f"{AGENT_SERVICE_URL}/conversations/{conversation_id}/interrupt",
                json={"message_id": message_id}
            )
    except Exception as e:
        logger.warning(f"Failed to interrupt agent service for message {message_id}: {e}")

    # Update message status
    await message.update({
        "$set": {
            "status": MessageStatus.CANCELLED,
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": {
                **message.metadata,
                "cancelled_at": datetime.utcnow().isoformat(),
                "cancellation_reason": "User requested cancellation",
            }
        }
    })

    return {"message": "Message cancelled successfully"}

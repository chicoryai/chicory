"""
Session cache for Claude SDK session management.

Lightweight Redis-based cache that stores only session_id per conversation,
enabling conversation resume without re-initialization.
"""
from typing import Optional
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class SessionCache:
    """
    Lightweight Redis cache for Claude SDK session_id only.

    Stores:
        session:{conversation_id} -> session_id

    TTL: 24 hours (configurable)
    """

    PREFIX = "session:"
    DEFAULT_TTL = 86400  # 24 hours

    def __init__(self, redis_client: redis.Redis, ttl: int = DEFAULT_TTL):
        self.redis = redis_client
        self.ttl = ttl

    async def get_session_id(self, conversation_id: str) -> Optional[str]:
        """
        Get cached session_id for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            The cached session_id or None if not found
        """
        session_id = await self.redis.get(f"{self.PREFIX}{conversation_id}")
        if session_id:
            logger.debug(f"[SESSION_CACHE] Found cached session for {conversation_id}: {session_id}")
        return session_id

    async def set_session_id(self, conversation_id: str, session_id: str) -> None:
        """
        Cache session_id with TTL.

        Args:
            conversation_id: The conversation ID
            session_id: The Claude SDK session ID to cache
        """
        await self.redis.setex(
            f"{self.PREFIX}{conversation_id}",
            self.ttl,
            session_id
        )
        logger.debug(f"[SESSION_CACHE] Cached session for {conversation_id}: {session_id}")

    async def delete(self, conversation_id: str) -> None:
        """
        Remove cached session (on conversation archive).

        Args:
            conversation_id: The conversation ID to remove
        """
        await self.redis.delete(f"{self.PREFIX}{conversation_id}")
        logger.debug(f"[SESSION_CACHE] Deleted session cache for {conversation_id}")

    async def exists(self, conversation_id: str) -> bool:
        """
        Check if a session is cached for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if cached, False otherwise
        """
        return await self.redis.exists(f"{self.PREFIX}{conversation_id}") > 0

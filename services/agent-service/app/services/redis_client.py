"""
Redis client singleton for agent-service.

Provides a lazy-initialized Redis client with connection pooling.
Supports both standard Redis and Redis Cluster (AWS MemoryDB).
"""
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
from typing import Optional, Union
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global lazy-initialized client
_redis_client: Optional[Union[redis.Redis, RedisCluster]] = None


async def get_redis_client() -> Union[redis.Redis, RedisCluster]:
    """
    Get or create Redis client with connection pooling.

    Uses RedisCluster when REDIS_CLUSTER_MODE is True (for AWS MemoryDB),
    otherwise uses standard Redis client for local development.

    Returns:
        Redis client instance (standard or cluster)
    """
    global _redis_client
    if _redis_client is None:
        logger.info(f"[REDIS] Initializing Redis client: {settings.REDIS_URL}")
        logger.info(f"[REDIS] Cluster mode: {settings.REDIS_CLUSTER_MODE}")

        if settings.REDIS_CLUSTER_MODE:
            # Use cluster client for AWS MemoryDB
            _redis_client = RedisCluster.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("[REDIS] Using RedisCluster client for AWS MemoryDB")
        else:
            # Standard client for local development
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=100,
                health_check_interval=30,
            )
            logger.info("[REDIS] Using standard Redis client")
    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection (for shutdown)."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("[REDIS] Client connection closed")

"""
Memory cache utilities for workers.

This replaces the LangChain-based caching with a simpler Redis-based approach.
Claude Agent SDK doesn't require LLM caching (handled by Anthropic).
"""
import os
import json
import hashlib
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class MemoryCache:
    """Simple in-memory cache for agent state and conversation history."""

    def __init__(self, cache_dir: Optional[str] = None):
        self._cache: Dict[str, Any] = {}
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        os.makedirs(self.cache_dir, exist_ok=True)

    @staticmethod
    def _get_default_cache_dir() -> str:
        home_path = os.getenv("HOME_PATH", "/app")
        data_path = os.getenv("BASE_DIR", os.path.join(home_path, "data"))
        project_name = os.environ.get('PROJECT', 'default').lower()
        return os.environ.get("CACHE_PATH", os.path.join(data_path, project_name, ".cache"))

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value in cache."""
        self._cache[key] = value

    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def get_conversation_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation state."""
        return f"conv:{conversation_id}"

    def save_conversation_state(self, conversation_id: str, state: Dict[str, Any]) -> None:
        """Save conversation state to cache."""
        key = self.get_conversation_key(conversation_id)
        self.set(key, state)

    def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation state from cache."""
        key = self.get_conversation_key(conversation_id)
        return self.get(key)


class RedisMemoryCache(MemoryCache):
    """Redis-backed memory cache for distributed workers."""

    def __init__(self, redis_url: Optional[str] = None, cache_dir: Optional[str] = None):
        super().__init__(cache_dir)
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis = None

    @property
    def redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            import redis
            self._redis = redis.from_url(self.redis_url)
        return self._redis

    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis cache."""
        value = self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in Redis cache with optional TTL."""
        serialized = json.dumps(value)
        if ttl:
            self.redis.setex(key, ttl, serialized)
        else:
            self.redis.set(key, serialized)

    def delete(self, key: str) -> None:
        """Delete a value from Redis cache."""
        self.redis.delete(key)


# Singleton instance
_memory_cache: Optional[MemoryCache] = None


def get_memory_cache(use_redis: bool = False) -> MemoryCache:
    """Get or create the memory cache singleton."""
    global _memory_cache
    if _memory_cache is None:
        if use_redis:
            _memory_cache = RedisMemoryCache()
        else:
            _memory_cache = MemoryCache()
    return _memory_cache

"""
Redis cache service with async support.

Provides high-level caching operations with automatic serialization.
"""

import json
from typing import Any, Optional, List, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings


class CacheService:
    """
    High-level Redis cache service.

    Features:
    - Automatic JSON serialization
    - TTL support
    - Bulk operations
    - Pattern-based deletion
    - Connection pooling
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )

    async def close(self) -> None:
        """Close Redis connections."""
        if self._pool:
            await self._pool.disconnect()

    @property
    def redis(self) -> "Redis":
        """Get Redis client."""
        if self._pool is None:
            raise RuntimeError("Cache service not connected. Call connect() first.")
        return redis.Redis(connection_pool=self._pool)

    # =========================================================================
    # Basic Operations
    # =========================================================================

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value by key with automatic deserialization."""
        value = await self.redis.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """Set key-value pair with optional TTL."""
        if isinstance(value, (dict, list, tuple, set)):
            value = json.dumps(value)
        elif not isinstance(value, (str, int, float, bool)):
            value = json.dumps(value, default=str)

        ttl_seconds = None
        if ttl:
            ttl_seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl

        return await self.redis.set(key, value, ex=ttl_seconds)

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        if not keys:
            return 0
        return await self.redis.delete(*keys)

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        return await self.redis.exists(*keys)

    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set TTL on existing key."""
        seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl
        return await self.redis.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for key."""
        return await self.redis.ttl(key)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def mget(self, *keys: str) -> List[Any]:
        """Get multiple values."""
        values = await self.redis.mget(keys)
        results = []
        for value in values:
            if value is None:
                results.append(None)
            else:
                try:
                    results.append(json.loads(value))
                except json.JSONDecodeError:
                    results.append(value)
        return results

    async def mset(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """Set multiple key-value pairs."""
        # Serialize values
        serialized = {}
        for k, v in mapping.items():
            if isinstance(v, (dict, list, tuple, set)):
                serialized[k] = json.dumps(v)
            elif not isinstance(v, (str, int, float, bool)):
                serialized[k] = json.dumps(v, default=str)
            else:
                serialized[k] = v

        result = await self.redis.mset(serialized)

        # Apply TTL if provided
        if ttl:
            for key in mapping.keys():
                await self.redis.expire(key, ttl)

        return result

    # =========================================================================
    # Increment/Decrement
    # =========================================================================

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment value."""
        return await self.redis.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement value."""
        return await self.redis.decrby(key, amount)

    # =========================================================================
    # Hash Operations
    # =========================================================================

    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set hash field."""
        if isinstance(value, (dict, list, tuple, set)):
            value = json.dumps(value)
        return await self.redis.hset(name, key, value)

    async def hget(self, name: str, key: str) -> Any:
        """Get hash field."""
        value = await self.redis.hget(name, key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def hgetall(self, name: str) -> dict:
        """Get all hash fields."""
        data = await self.redis.hgetall(name)
        result = {}
        for k, v in data.items():
            try:
                result[k] = json.loads(v)
            except json.JSONDecodeError:
                result[k] = v
        return result

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        return await self.redis.hdel(name, *keys)

    # =========================================================================
    # Set Operations
    # =========================================================================

    async def sadd(self, name: str, *values: str) -> int:
        """Add to set."""
        return await self.redis.sadd(name, *values)

    async def srem(self, name: str, *values: str) -> int:
        """Remove from set."""
        return await self.redis.srem(name, *values)

    async def smembers(self, name: str) -> set:
        """Get set members."""
        return await self.redis.smembers(name)

    async def sismember(self, name: str, value: str) -> bool:
        """Check set membership."""
        return await self.redis.sismember(name, value)

    # =========================================================================
    # Pattern Operations
    # =========================================================================

    async def keys(self, pattern: str) -> List[str]:
        """Find keys matching pattern."""
        return await self.redis.keys(pattern)

    async def scan(self, pattern: str, count: int = 100) -> List[str]:
        """Scan keys matching pattern (non-blocking)."""
        keys = []
        async for key in self.redis.scan_iter(match=pattern, count=count):
            keys.append(key)
        return keys

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        keys = await self.scan(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0

    # =========================================================================
    # Pub/Sub
    # =========================================================================

    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel."""
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        return await self.redis.publish(channel, message)

    async def subscribe(self, *channels: str):
        """Subscribe to channels."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub

    # =========================================================================
    # Health Check
    # =========================================================================

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return await self.redis.ping()
        except Exception:
            return False

    async def info(self) -> dict:
        """Get Redis server info."""
        return await self.redis.info()


# Global cache instance
cache_service = CacheService()


async def get_cache() -> CacheService:
    """Dependency for cache service."""
    if cache_service._pool is None:
        await cache_service.connect()
    return cache_service
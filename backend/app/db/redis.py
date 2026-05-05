"""
Redis Client
Provides async Redis connection for caching and session management
"""
import redis.asyncio as redis
from app.core.config import settings

# Global Redis connection pool
_redis_client: redis.Redis = None


async def get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
            await _redis_client.ping()
        except Exception as e:
            print("Redis connection failed:", e)
            return None
    return _redis_client


async def close_redis():
    """Close Redis connection on shutdown"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
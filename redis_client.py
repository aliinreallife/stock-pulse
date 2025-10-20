import os
import redis.asyncio as redis

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = await redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    return _redis



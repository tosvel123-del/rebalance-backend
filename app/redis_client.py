import redis.asyncio as redis
from app.config import settings

class DummyRedis:
    def __init__(self):
        self._store = {}
    async def get(self, key):
        return self._store.get(key)
    async def set(self, key, value, ex=None):
        self._store[key] = str(value)
        return True
    async def delete(self, key):
        self._store.pop(key, None)
        return True

try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_timeout=2.0,
    )
except Exception:
    redis_client = DummyRedis()

async def get_redis():
    return redis_client


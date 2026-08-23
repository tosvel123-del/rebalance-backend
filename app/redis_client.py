import redis.asyncio as redis
from time import monotonic
from app.config import settings

class DummyRedis:
    def __init__(self):
        self._store = {}
    async def get(self, key):
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and expires_at <= monotonic():
            self._store.pop(key, None)
            return None
        return value
    async def set(self, key, value, ex=None):
        expires_at = monotonic() + ex if ex else None
        self._store[key] = (str(value), expires_at)
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

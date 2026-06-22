"""اتصال Redis - برای کش، rate-limit آنتی‌فرود و FSM storage ربات"""
import redis.asyncio as redis

from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

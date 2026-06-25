"""سرویس Trust Score / آنتی‌فرود پایه (بخش VIP خودکار حذف شد - جایگزین: panel_service.py)"""
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, FraudFlag, Participation
from app.redis_client import redis_client


def clamp_trust(value: int) -> int:
    return max(0, min(100, value))


async def adjust_trust(session: AsyncSession, user: User, delta: int):
    user.trust_score = clamp_trust(user.trust_score + delta)


async def flag_fraud(session: AsyncSession, user: User, flag_type: str, details: str | None = None, trust_penalty: int = 10):
    session.add(FraudFlag(user_id=user.id, flag_type=flag_type, details=details))
    await adjust_trust(session, user, -trust_penalty)


async def is_rate_limited(user_id: int, action: str, max_count: int, window_seconds: int) -> bool:
    """
    rate-limit ساده روی Redis. مثلا جلوگیری از جوین زدن بیش از حد سریع
    (نشونه‌ی بات/فارم اکانت). برمی‌گردونه True یعنی محدود شده.
    """
    key = f"ratelimit:{action}:{user_id}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)
    return current > max_count


async def recent_join_count(session: AsyncSession, user_id: int, minutes: int = 1) -> int:
    since = datetime.utcnow() - timedelta(minutes=minutes)
    result = await session.execute(
        select(func.count(Participation.id)).where(
            Participation.user_id == user_id, Participation.joined_at >= since
        )
    )
    return result.scalar_one()

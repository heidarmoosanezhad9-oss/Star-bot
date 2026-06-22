"""سرویس VIP / Trust Score / آنتی‌فرود پایه"""
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, VIPLevel, FraudFlag, Participation
from app.redis_client import redis_client


async def check_and_upgrade_vip(session: AsyncSession, user: User):
    """بر اساس کل الماس کسب‌شده در طول عمر، سطح VIP رو آپدیت می‌کنه"""
    result = await session.execute(
        select(VIPLevel)
        .where(VIPLevel.min_total_earned <= user.total_diamonds_earned)
        .order_by(VIPLevel.min_total_earned.desc())
        .limit(1)
    )
    level = result.scalar_one_or_none()
    if level and user.vip_level_id != level.id:
        user.vip_level_id = level.id


async def get_reward_multiplier(session: AsyncSession, user: User) -> float:
    if not user.vip_level_id:
        return 1.0
    level = await session.get(VIPLevel, user.vip_level_id)
    return level.reward_multiplier if level else 1.0


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

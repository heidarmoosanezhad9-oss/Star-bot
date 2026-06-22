"""سرویس رفرال: ثبت زیرمجموعه و پاداش بعد از اولین اقدام واقعی (نه فقط استارت زدن)"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Referral, ActionType
from app.services.wallet_service import add_diamonds
from app.services.vip_trust_service import get_reward_multiplier
from app.services.settings_service import get_setting
from app.services.progression_service import check_achievements, progress_mission


async def register_referral(session: AsyncSession, referee: User, referrer_id: int):
    """فقط رکورد رفرال رو می‌سازه - پاداش بعد از اولین جوین واقعی داده میشه تا فیک‌ریفرال کم بشه"""
    if referrer_id == referee.id:
        return
    referrer = await session.get(User, referrer_id)
    if referrer is None or referrer.is_banned:
        return

    existing = await session.execute(select(Referral).where(Referral.referee_id == referee.id))
    if existing.scalar_one_or_none():
        return

    session.add(Referral(referrer_id=referrer_id, referee_id=referee.id))
    referee.referred_by = referrer_id
    await session.flush()


async def reward_referral_if_eligible(session: AsyncSession, referee_id: int):
    """وقتی کاربر زیرمجموعه برای اولین بار یک جوین موفق ثبت می‌کنه، به دعوت‌کننده پاداش بده"""
    result = await session.execute(
        select(Referral).where(Referral.referee_id == referee_id, Referral.reward_given == False)  # noqa: E712
    )
    referral = result.scalar_one_or_none()
    if referral is None:
        return

    referrer = await session.get(User, referral.referrer_id)
    if referrer is None:
        return

    base_reward = await get_setting(session, "referral_reward", settings.DEFAULT_REFERRAL_REWARD)
    multiplier = await get_reward_multiplier(session, referrer)
    amount = int(base_reward * multiplier)

    await add_diamonds(session, referrer, amount, ActionType.REFERRAL_REWARD, meta=f"referee:{referee_id}")
    referral.reward_given = True
    referrer.referrals_count += 1
    await progress_mission(session, referrer, "invite_users", increment=1)
    await check_achievements(session, referrer)

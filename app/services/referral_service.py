"""
سرویس رفرال: ثبت زیرمجموعه و پاداش بعد از اینکه زیرمجموعه حداقل N کانال
از کانال سفارش‌ها عضو شد (ضد فیک‌ریفرال) - نه فقط با استارت زدن.
"""
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Referral, ActionType, Participation
from app.services.wallet_service import add_diamonds
from app.services.panel_service import get_user_rates
from app.services.settings_service import get_setting
from app.services.progression_service import check_achievements, progress_mission


async def register_referral(session: AsyncSession, referee: User, referrer_id: int):
    """فقط رکورد رفرال رو می‌سازه - پاداش بعد از رسیدن به حد نصاب جوین واقعی داده میشه"""
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


async def reward_referral_if_eligible(session: AsyncSession, bot: Bot, referee_id: int):
    """وقتی زیرمجموعه به حد نصاب جوین موفق رسید، به دعوت‌کننده پاداش بده و خبرش رو بده"""
    result = await session.execute(
        select(Referral).where(Referral.referee_id == referee_id, Referral.reward_given == False)  # noqa: E712
    )
    referral = result.scalar_one_or_none()
    if referral is None:
        return

    min_joins = await get_setting(session, "referral_min_joins", 3)
    joins_count = (await session.execute(
        select(func.count(Participation.id)).where(
            Participation.user_id == referee_id, Participation.rewarded == True  # noqa: E712
        )
    )).scalar_one()
    if joins_count < min_joins:
        return

    referrer = await session.get(User, referral.referrer_id)
    if referrer is None:
        return

    rates = await get_user_rates(session, referrer)
    amount = rates["referral_reward"]

    await add_diamonds(session, referrer, amount, ActionType.REFERRAL_REWARD, meta=f"referee:{referee_id}")
    referral.reward_given = True
    referrer.referrals_count += 1
    await progress_mission(session, referrer, "invite_users", increment=1)
    await check_achievements(session, referrer)

    try:
        await bot.send_message(
            referrer.id,
            f"🎉 زیرمجموعه‌ت فعال شد و {amount} ⭐ به کیفت اضافه شد!"
        )
    except TelegramForbiddenError:
        pass

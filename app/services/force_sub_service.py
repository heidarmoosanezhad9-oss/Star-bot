"""سرویس عضویت اجباری (Force Subscribe)"""
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, ForceSubChannel, ForceSubJoin, ActionType
from app.services.wallet_service import penalize
from app.services.settings_service import get_setting


async def get_active_channels(session: AsyncSession) -> list[ForceSubChannel]:
    result = await session.execute(
        select(ForceSubChannel).where(ForceSubChannel.is_active == True).order_by(ForceSubChannel.sort_order)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_missing_channels(bot: Bot, session: AsyncSession, user: User) -> list[ForceSubChannel]:
    """
    هر بار که صدا زده می‌شه، عضویت رو زنده از تلگرام چک می‌کنه - بدون کش و بدون بای‌پس،
    تا کاربری که بعد از تایید اولیه از کانال لفت داده، فوراً (همون کلیک بعدی) دوباره گیت بشه.
    """
    channels = await get_active_channels(session)
    missing = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch.chat_id, user.id)
            is_member = member.status in ("member", "administrator", "creator")
        except TelegramBadRequest:
            is_member = False

        if is_member:
            await _record_join_if_new(session, user.id, ch.id)
        else:
            missing.append(ch)
    return missing


async def _record_join_if_new(session: AsyncSession, user_id: int, channel_id: int):
    existing = await session.execute(
        select(ForceSubJoin).where(
            ForceSubJoin.user_id == user_id, ForceSubJoin.channel_id == channel_id, ForceSubJoin.left_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is None:
        session.add(ForceSubJoin(user_id=user_id, channel_id=channel_id))
        await session.flush()


def build_force_sub_link(channel: ForceSubChannel) -> str:
    if channel.username:
        return f"https://t.me/{channel.username}"
    return channel.invite_link or "https://t.me/"


async def handle_force_sub_left(session: AsyncSession, channel_chat_id: int, left_user_id: int):
    """جریمه‌ی لفت زودهنگام از کانال/گروه اسپانسر"""
    result = await session.execute(select(ForceSubChannel).where(ForceSubChannel.chat_id == channel_chat_id))
    channel = result.scalar_one_or_none()
    if channel is None:
        return

    join_row = await session.execute(
        select(ForceSubJoin).where(
            ForceSubJoin.user_id == left_user_id, ForceSubJoin.channel_id == channel.id,
            ForceSubJoin.left_at.is_(None),
        )
    )
    join_row = join_row.scalar_one_or_none()
    if join_row is None:
        return

    now = datetime.utcnow()
    join_row.left_at = now

    leave_penalty_days = await get_setting(session, "leave_penalty_days", 4)
    days_since_join = (now - join_row.joined_at).days
    if days_since_join < leave_penalty_days and not join_row.penalized:
        penalty_amount = await get_setting(session, "sponsor_leave_penalty", 5)
        user = await session.get(User, left_user_id)
        if user and penalty_amount > 0:
            await penalize(session, user, penalty_amount, ActionType.SPONSOR_LEAVE_PENALTY, meta=f"channel:{channel.id}")
            join_row.penalized = True

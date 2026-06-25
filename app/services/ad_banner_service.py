"""سرویس تبلیغ کانال - بنر داخل بات بر اساس تعداد نمایش (جایگزین تبلیغ ساعتی قبلی)"""
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Channel, AdBanner, AdBannerStatus, ActionType
from app.services.channel_service import get_or_create_channel
from app.services.wallet_service import spend_diamonds
from app.services.settings_service import get_setting
from app.services.order_service import OrderError


async def validate_channel_for_ad(bot: Bot, chat_id: int) -> dict:
    try:
        chat = await bot.get_chat(chat_id)
    except TelegramBadRequest as e:
        return {"ok": False, "error": f"دسترسی به کانال ممکن نشد: {e.message}"}
    return {"ok": True, "title": chat.title, "username": chat.username, "chat_id": chat.id,
            "description": getattr(chat, "description", None)}


async def create_ad_banner(session: AsyncSession, bot: Bot, user: User, chat_id: int, target_impressions: int) -> AdBanner:
    if user.is_banned:
        raise OrderError("حساب شما مسدود است.")

    check = await validate_channel_for_ad(bot, chat_id)
    if not check["ok"]:
        raise OrderError(check["error"])

    channel = await get_or_create_channel(
        session, check["chat_id"], check.get("username"), check.get("title"), user.id,
        description=check.get("description"),
    )

    price_per_view = await get_setting(session, "price_per_ad_view", 1)
    price_total = int(price_per_view * target_impressions)

    ok = await spend_diamonds(session, user, price_total, ActionType.ORDER_PAYMENT, meta=f"ad:{channel.chat_id}")
    if not ok:
        raise OrderError(f"موجودی استارز کافی نیست. هزینه‌ی این تبلیغ {price_total} ⭐ است.")

    banner = AdBanner(
        user_id=user.id, channel_id=channel.id, target_impressions=target_impressions, price_total=price_total,
    )
    session.add(banner)
    await session.flush()
    return banner


async def get_random_active_banner(session: AsyncSession) -> AdBanner | None:
    result = await session.execute(
        select(AdBanner).where(AdBanner.status == AdBannerStatus.ACTIVE.value).order_by(AdBanner.shown_count.asc()).limit(1)
    )
    return result.scalar_one_or_none()


async def record_impression(session: AsyncSession, banner: AdBanner):
    banner.shown_count += 1
    if banner.shown_count >= banner.target_impressions:
        banner.status = AdBannerStatus.COMPLETED.value
        banner.completed_at = datetime.utcnow()
    await session.flush()

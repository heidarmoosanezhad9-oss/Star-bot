"""سرویس فروشگاه - خرید پنل یا استارز با تایید دستی ادمین"""
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User, PanelTier, PanelPrice, StarPackage, PurchaseRequest, PurchaseStatus, ActionType,
)
from app.services.wallet_service import add_diamonds
from app.services.panel_service import grant_panel


async def list_panel_prices(session: AsyncSession) -> list[PanelPrice]:
    result = await session.execute(
        select(PanelPrice).where(PanelPrice.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def list_star_packages(session: AsyncSession) -> list[StarPackage]:
    result = await session.execute(
        select(StarPackage).where(StarPackage.is_active == True).order_by(StarPackage.sort_order)  # noqa: E712
    )
    return list(result.scalars().all())


async def create_panel_purchase_request(session: AsyncSession, user: User, panel_price_id: int) -> PurchaseRequest:
    req = PurchaseRequest(user_id=user.id, request_type="panel", panel_price_id=panel_price_id)
    session.add(req)
    await session.flush()
    return req


async def create_star_purchase_request(session: AsyncSession, user: User, star_package_id: int) -> PurchaseRequest:
    req = PurchaseRequest(user_id=user.id, request_type="stars", star_package_id=star_package_id)
    session.add(req)
    await session.flush()
    return req


async def approve_purchase(session: AsyncSession, bot: Bot, request_id: int, approved_by: int) -> str:
    req = await session.get(PurchaseRequest, request_id)
    if req is None or req.status != PurchaseStatus.PENDING.value:
        return "این درخواست دیگه در دسترس نیست."

    buyer = await session.get(User, req.user_id)
    if buyer is None:
        return "خریدار پیدا نشد."

    if req.request_type == "panel":
        price = await session.get(PanelPrice, req.panel_price_id)
        tier = await session.get(PanelTier, price.panel_tier_id) if price else None
        if price is None or tier is None:
            return "این پنل دیگه در دسترس نیست."
        await grant_panel(session, buyer, price)
        notify_text = f"✅ خریدت تایید شد! پنل {tier.emoji} {tier.name} به مدت {price.duration_days} روز فعال شد."
    else:
        package = await session.get(StarPackage, req.star_package_id)
        if package is None:
            return "این بسته دیگه در دسترس نیست."
        await add_diamonds(session, buyer, package.amount_stars, ActionType.STAR_TOPUP, meta=f"pkg:{package.id}")
        notify_text = f"✅ خریدت تایید شد! {package.amount_stars} ⭐ به کیفت اضافه شد."

    req.status = PurchaseStatus.APPROVED.value
    req.decided_at = datetime.utcnow()
    req.decided_by = approved_by
    await session.flush()

    try:
        await bot.send_message(buyer.id, notify_text)
    except TelegramForbiddenError:
        pass

    return notify_text


async def reject_purchase(session: AsyncSession, bot: Bot, request_id: int, rejected_by: int) -> str:
    req = await session.get(PurchaseRequest, request_id)
    if req is None or req.status != PurchaseStatus.PENDING.value:
        return "این درخواست دیگه در دسترس نیست."

    req.status = PurchaseStatus.REJECTED.value
    req.decided_at = datetime.utcnow()
    req.decided_by = rejected_by
    await session.flush()

    buyer = await session.get(User, req.user_id)
    if buyer:
        try:
            await bot.send_message(buyer.id, "❌ درخواست خریدت رد شد. برای پیگیری به پشتیبانی پیام بده.")
        except TelegramForbiddenError:
            pass

    return "رد شد."

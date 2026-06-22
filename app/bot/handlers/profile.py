"""هندلر پروفایل کاربر: موجودی، VIP، تراست‌اسکور، سفارش‌های خودش"""
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Order, VIPLevel
from app.services.wallet_service import get_or_create_wallet

router = Router(name="profile")


@router.message(F.text == "👤 پروفایل من")
async def show_profile(message: Message, session: AsyncSession, user: User):
    vip_name = "بدون سطح"
    if user.vip_level_id:
        level = await session.get(VIPLevel, user.vip_level_id)
        if level:
            vip_name = level.name

    wallet = await get_or_create_wallet(session, user.id)
    text = (
        f"👤 <b>پروفایل تو</b>\n\n"
        f"💎 موجودی الماس: {wallet.diamonds}\n"
        f"⭐ سطح VIP: {vip_name}\n"
        f"🤝 امتیاز اعتماد: {user.trust_score}/100\n"
        f"👥 تعداد زیرمجموعه: {user.referrals_count}\n"
        f"✅ سفارش‌های تکمیل‌شده: {user.orders_completed_count}\n"
        f"🚪 تعداد لفت ثبت‌شده: {user.leaves_count}\n"
    )
    await message.answer(text)

    result = await session.execute(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(5)
    )
    orders = result.scalars().all()
    if orders:
        lines = ["🧾 <b>۵ سفارش آخر تو:</b>"]
        for o in orders:
            lines.append(f"#{o.id} | {o.order_type} | {o.progress_count}/{o.target_count} | {o.status}")
        await message.answer("\n".join(lines))

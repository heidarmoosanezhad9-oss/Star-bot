"""هندلر کسب الماس: پاداش روزانه + لیست تسک‌های فعال + پردازش کلیک جوین"""
from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Order, Channel, OrderStatus, ActionType
from app.services.wallet_service import add_diamonds
from app.services.settings_service import get_setting
from app.services.progression_service import progress_mission
from app.services.order_service import handle_collector_click

router = Router(name="earn")


@router.message(F.text == "💎 کسب الماس")
async def earn_menu(message: Message, session: AsyncSession, user: User):
    buttons = []

    if user.last_daily_claim != date.today():
        buttons.append([InlineKeyboardButton(text="🎁 دریافت پاداش روزانه", callback_data="daily_claim")])

    result = await session.execute(
        select(Order, Channel)
        .join(Channel, Channel.id == Order.channel_id)
        .where(Order.status.in_([OrderStatus.IN_PROGRESS.value, OrderStatus.REFILLING.value]))
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    rows = result.all()

    join_reward = await get_setting(session, "join_reward", settings.DEFAULT_JOIN_REWARD)

    for order, channel in rows:
        if order.user_id == user.id:
            continue
        label = f"@{channel.username}" if channel.username else (channel.title or "کانال")
        icon = "🚀" if order.order_type == "member" else "👀"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {label} (+{join_reward}💎)", callback_data=f"join:{order.id}"
        )])

    if not buttons:
        await message.answer("فعلاً تسک فعالی برای کسب الماس نیست. بعداً دوباره چک کن 🙂")
        return

    await message.answer(
        "💎 <b>کسب الماس</b>\n\nبا انجام تسک‌های زیر، الماس فوری بگیر:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "daily_claim")
async def claim_daily(callback: CallbackQuery, session: AsyncSession, user: User):
    if user.last_daily_claim == date.today():
        await callback.answer("امروز قبلاً پاداشت رو گرفتی ✅", show_alert=True)
        return

    reward = await get_setting(session, "daily_reward", 5)
    await add_diamonds(session, user, reward, ActionType.DAILY_REWARD, meta="daily")
    user.last_daily_claim = date.today()
    await progress_mission(session, user, "stay_active", increment=1)

    await callback.answer(f"🎉 {reward} 💎 پاداش روزانه گرفتی!", show_alert=True)


@router.callback_query(F.data.startswith("join:"))
async def on_join_click(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    result = await handle_collector_click(session, bot, order_id, user)
    await callback.answer(result["message"], show_alert=True)

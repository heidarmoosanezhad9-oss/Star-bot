"""هندلر کسب استارز: پاداش روزانه + لینک کانال جمع‌آوری + بنر تبلیغاتی + پردازش کلیک جوین"""
from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, ActionType
from app.services.wallet_service import add_diamonds
from app.services.settings_service import get_setting
from app.services.progression_service import progress_mission
from app.services.order_service import handle_collector_click
from app.services.ad_banner_service import get_random_active_banner, record_impression
from app.models import Channel

router = Router(name="earn")


@router.message(F.text == "⭐ کسب استارز")
async def earn_menu(message: Message, session: AsyncSession, user: User):
    buttons = []

    if user.last_daily_claim != date.today():
        buttons.append([InlineKeyboardButton(text="🎁 دریافت پاداش روزانه", callback_data="daily_claim")])

    buttons.append([InlineKeyboardButton(text="⭐ برو توی کانال و کسب استارز", url=settings.COLLECTOR_CHANNEL_LINK)])

    await message.answer(
        "⭐ <b>کسب استارز</b>\n\n"
        "🎁 پاداش روزانه‌ت رو از همینجا بگیر.\n"
        "بعدش برو توی کانال جمع‌آوری، توی هر سفارشی که هست عضو شو و استارز فوری بگیر!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )

    banner = await get_random_active_banner(session)
    if banner:
        channel = await session.get(Channel, banner.channel_id)
        if channel:
            link = f"https://t.me/{channel.username}" if channel.username else (channel.invite_link or "")
            await record_impression(session, banner)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👀 مشاهده کانال", url=link)]]) if link else None
            await message.answer(
                f"📣 <b>تبلیغ</b>\n\n{channel.title or '-'}\n{channel.description or ''}".strip(),
                reply_markup=kb,
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

    await callback.answer(f"🎉 {reward} ⭐ پاداش روزانه گرفتی!", show_alert=True)


@router.callback_query(F.data.startswith("join:"))
async def on_join_click(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    result = await handle_collector_click(session, bot, order_id, user)
    await callback.answer(result["message"], show_alert=True)

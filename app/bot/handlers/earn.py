"""هندلر کسب الماس: پاداش روزانه + لینک کانال جمع‌آوری + پردازش کلیک جوین"""
from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.models import User, ActionType
from app.services.wallet_service import add_diamonds
from app.services.settings_service import get_setting
from app.services.progression_service import progress_mission
from app.services.order_service import handle_collector_click

router = Router(name="earn")


@router.message(F.text == "💎 کسب الماس")
async def earn_menu(message: Message, session):
    buttons = []

    if message.from_user:
        pass

    buttons.append([InlineKeyboardButton(text="💎 برو توی کانال و کسب الماس", url=settings.COLLECTOR_CHANNEL_LINK)])

    await message.answer(
        "💎 <b>کسب الماس</b>\n\n"
        "🎁 پاداش روزانه‌ت رو هر روز از همینجا بگیر:\n"
        "با عضو شدن توی کانال‌های داخل کانال جمع‌آوری، الماس بیشتری کسب کن!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 دریافت پاداش روزانه", callback_data="daily_claim")],
            [InlineKeyboardButton(text="💎 برو توی کانال و کسب الماس", url=settings.COLLECTOR_CHANNEL_LINK)],
        ]),
    )


@router.callback_query(F.data == "daily_claim")
async def claim_daily(callback: CallbackQuery, session, user: User):
    if user.last_daily_claim == date.today():
        await callback.answer("امروز قبلاً پاداشت رو گرفتی ✅", show_alert=True)
        return

    reward = await get_setting(session, "daily_reward", 5)
    await add_diamonds(session, user, reward, ActionType.DAILY_REWARD, meta="daily")
    user.last_daily_claim = date.today()
    await progress_mission(session, user, "stay_active", increment=1)

    await callback.answer(f"🎉 {reward} 💎 پاداش روزانه گرفتی!", show_alert=True)


@router.callback_query(F.data.startswith("join:"))
async def on_join_click(callback: CallbackQuery, session, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    result = await handle_collector_click(session, bot, order_id, user)
    await callback.answer(result["message"], show_alert=True)

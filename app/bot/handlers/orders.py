"""هندلر ثبت سفارش (ممبر/تبلیغ) با FSM - تایید کاملاً خودکار، بدون دخالت دستی ادمین"""
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, OrderType
from app.bot.keyboards import order_type_keyboard, cancel_keyboard, confirm_keyboard, main_menu
from app.services.order_service import (
    create_order, post_order_to_collector, OrderError,
    validate_channel_for_member_order, validate_channel_for_ad_order,
)
from app.services.settings_service import get_setting
from app.services.channel_service import get_or_create_channel

router = Router(name="orders")

MENU_TEXTS = {
    "💎 کسب الماس", "🛒 ثبت سفارش", "👤 پروفایل من", "👥 زیرمجموعه‌گیری",
    "🎯 ماموریت روزانه", "🎁 کد هدیه", "🎫 پشتیبانی", "🛠 پنل مدیریت", "ℹ️ راهنما",
}


class OrderStates(StatesGroup):
    waiting_channel = State()
    waiting_count = State()
    confirming = State()


@router.message(F.text == "🛒 ثبت سفارش")
async def order_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "چه نوع سفارشی می‌خوای ثبت کنی؟", reply_markup=order_type_keyboard()
    )


@router.callback_query(F.data.startswith("new_order:"))
async def choose_order_type(callback: CallbackQuery, state: FSMContext):
    order_type = callback.data.split(":")[1]
    await state.update_data(order_type=order_type)
    await state.set_state(OrderStates.waiting_channel)

    if order_type == OrderType.MEMBER.value:
        text = (
            "1️⃣ ربات رو به کانالت <b>ادمین</b> کن با دو دسترسی:\n"
            "«دعوت کاربران از طریق لینک» و «مدیریت چت»\n\n"
            "2️⃣ بعدش آیدی عددی یا یوزرنیم کانال رو همینجا بفرست (مثلا @mychannel)"
        )
    else:
        text = "یوزرنیم یا آیدی عددی کانالی که می‌خوای تبلیغ بشه رو بفرست (مثلا @mychannel)"

    await callback.message.edit_text(text, reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_flow(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("لغو شد.")
    await callback.answer()


def _parse_channel_input(text: str) -> str | int:
    text = text.strip()
    if "t.me/" in text:
        text = text.split("t.me/")[-1].split("?")[0].strip("/")
    if text.startswith("-100") and text.lstrip("-").isdigit():
        return int(text)
    if not text.startswith("@"):
        text = "@" + text
    return text


@router.message(OrderStates.waiting_channel)
async def receive_channel(message: Message, state: FSMContext, bot: Bot):
    if (message.text or "").strip() in MENU_TEXTS:
        await state.clear()
        await message.answer("ثبت سفارش لغو شد. از منو دوباره شروع کن.")
        return

    chat_ref = _parse_channel_input(message.text or "")
    try:
        chat = await bot.get_chat(chat_ref)
    except TelegramBadRequest:
        await message.answer("کانال پیدا نشد. دوباره یوزرنیم یا آیدی عددی رو بفرست.", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    if data["order_type"] == OrderType.MEMBER.value:
        check = await validate_channel_for_member_order(bot, chat.id)
    else:
        check = await validate_channel_for_ad_order(bot, chat.id)

    if not check["ok"]:
        await message.answer(f"⚠️ {check['error']}\n\nبعد از رفع مشکل دوباره بفرست.", reply_markup=cancel_keyboard())
        return

    await state.update_data(chat_id=chat.id, title=chat.title, username=chat.username)
    await state.set_state(OrderStates.waiting_count)

    if data["order_type"] == OrderType.MEMBER.value:
        await message.answer("چند نفر ممبر می‌خوای؟ (فقط عدد بفرست، مثلا 100)", reply_markup=cancel_keyboard())
    else:
        await message.answer("چند ساعت می‌خوای تبلیغ نمایش داده شه؟ (فقط عدد بفرست، مثلا 24)", reply_markup=cancel_keyboard())


@router.message(OrderStates.waiting_count)
async def receive_count(message: Message, state: FSMContext, session: AsyncSession):
    raw = (message.text or "").strip()
    if raw in MENU_TEXTS:
        await state.clear()
        await message.answer("ثبت سفارش لغو شد. از منو دوباره شروع کن.")
        return

    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("لطفاً فقط یک عدد صحیح مثبت بفرست.", reply_markup=cancel_keyboard())
        return

    target_count = int(raw)
    data = await state.get_data()
    order_type = data["order_type"]

    if order_type == OrderType.MEMBER.value:
        price_per_unit = await get_setting(session, "price_per_member", settings.PRICE_PER_MEMBER)
    else:
        price_per_unit = await get_setting(session, "price_per_ad_hour", settings.PRICE_PER_AD_HOUR)

    price_total = int(price_per_unit * target_count)
    await state.update_data(target_count=target_count, price_total=price_total)
    await state.set_state(OrderStates.confirming)

    label = f"@{data['username']}" if data.get("username") else data.get("title")
    unit = "نفر ممبر" if order_type == OrderType.MEMBER.value else "ساعت تبلیغ"
    await message.answer(
        f"📋 <b>پیش‌نمایش سفارش</b>\n\n"
        f"کانال: {label}\n"
        f"مقدار: {target_count} {unit}\n"
        f"هزینه: {price_total} 💎\n\n"
        f"تایید می‌کنی؟",
        reply_markup=confirm_keyboard("order"),
    )


@router.callback_query(F.data == "confirm:order", OrderStates.confirming)
async def confirm_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, bot: Bot):
    data = await state.get_data()
    try:
        order = await create_order(
            session, bot, user,
            chat_id=data["chat_id"],
            order_type=OrderType(data["order_type"]),
            target_count=data["target_count"],
        )
        channel = await get_or_create_channel(session, data["chat_id"], data.get("username"), data.get("title"), user.id)
        await post_order_to_collector(bot, session, order, channel)
    except OrderError as e:
        await callback.message.edit_text(f"❌ {e}")
        await state.clear()
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(
        f"✅ سفارش شماره {order.id} با موفقیت ثبت و تایید شد و الان توی کانال جمع‌آوری در حال نمایشه!\n"
        f"از منو می‌تونی پیشرفتش رو از «پروفایل من → سفارش‌های من» پیگیری کنی."
    )
    await callback.answer()

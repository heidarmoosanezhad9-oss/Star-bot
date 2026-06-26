"""هندلر ثبت سفارش (ممبر/تبلیغ) با FSM - تایید کاملاً خودکار، بدون دخالت دستی ادمین"""
import logging

from aiogram import Router, F, Bot
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Order, Channel
from app.bot.keyboards import order_type_keyboard, cancel_keyboard, confirm_keyboard
from app.services.order_service import (
    create_order, post_order_to_collector, OrderError, validate_channel_for_member_order,
)
from app.services.ad_banner_service import create_ad_banner, validate_channel_for_ad
from app.services.settings_service import get_setting
from app.config import settings as cfg
from app.redis_client import redis_client

router = Router(name="orders")
logger = logging.getLogger(__name__)

MENU_TEXTS = {
    "⭐ کسب استارز", "🛒 ثبت سفارش", "👤 پروفایل من", "👥 زیرمجموعه‌گیری",
    "🎯 ماموریت روزانه", "🎁 کد هدیه", "🎫 پشتیبانی", "🛠 پنل مدیریت", "ℹ️ راهنما",
    "🛍 فروشگاه", "📜 قوانین",
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

    if order_type == "member":
        text = (
            "1️⃣ ربات رو به کانال یا گروهت <b>ادمین</b> کن با دو دسترسی:\n"
            "«دعوت کاربران از طریق لینک» و «مدیریت چت»\n\n"
            "2️⃣ بعدش آیدی عددی یا یوزرنیم کانال/گروه رو همینجا بفرست (مثلا @mychannel)"
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
        await message.answer("کانال/گروه پیدا نشد. دوباره یوزرنیم یا آیدی عددی رو بفرست.", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    if data["order_type"] == "member":
        check = await validate_channel_for_member_order(bot, chat.id)
    else:
        check = await validate_channel_for_ad(bot, chat.id)

    if not check["ok"]:
        await message.answer(f"⚠️ {check['error']}\n\nبعد از رفع مشکل دوباره بفرست.", reply_markup=cancel_keyboard())
        return

    await state.update_data(chat_id=chat.id, title=chat.title, username=chat.username)
    await state.set_state(OrderStates.waiting_count)

    if data["order_type"] == "member":
        await message.answer("چند نفر ممبر می‌خوای؟ (فقط عدد بفرست، مثلا 100)", reply_markup=cancel_keyboard())
    else:
        await message.answer("چند بار نمایش داخل بات می‌خوای؟ (فقط عدد بفرست، مثلا 500)", reply_markup=cancel_keyboard())


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

    if order_type == "member":
        price_per_unit = await get_setting(session, "price_per_member", settings.PRICE_PER_MEMBER)
        unit = "نفر ممبر"
    else:
        price_per_unit = await get_setting(session, "price_per_ad_view", 1)
        unit = "بار نمایش"

    price_total = int(price_per_unit * target_count)
    await state.update_data(target_count=target_count, price_total=price_total)
    await state.set_state(OrderStates.confirming)

    label = f"@{data['username']}" if data.get("username") else data.get("title")
    await message.answer(
        f"📋 <b>پیش‌نمایش سفارش</b>\n\n"
        f"کانال: {label}\n"
        f"مقدار: {target_count} {unit}\n"
        f"هزینه: {price_total} ⭐\n\n"
        f"تایید می‌کنی؟",
        reply_markup=confirm_keyboard("order"),
    )


@router.callback_query(F.data == "confirm:order", OrderStates.confirming)
async def confirm_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, bot: Bot):
    data = await state.get_data()
    try:
        if data["order_type"] == "member":
            order = await create_order(session, bot, user, chat_id=data["chat_id"], target_count=data["target_count"])
            channel = await session.get(Channel, order.channel_id)
            await post_order_to_collector(bot, session, order, channel)
            success_text = (
                f"✅ سفارش شماره {order.id} با موفقیت ثبت و تایید شد و الان توی کانال جمع‌آوری در حال نمایشه!\n"
                f"از «پروفایل من» می‌تونی پیشرفتش رو پیگیری کنی."
            )
        else:
            banner = await create_ad_banner(session, bot, user, chat_id=data["chat_id"], target_impressions=data["target_count"])
            success_text = (
                f"✅ تبلیغت ثبت شد!\n"
                f"به مدت {banner.target_impressions} بار، بین کاربرایی که «⭐ کسب استارز» رو باز می‌کنن نمایش داده می‌شه."
            )
    except OrderError as e:
        await callback.message.edit_text(f"❌ {e}")
        await state.clear()
        await callback.answer()
        return
    except Exception:
        logger.exception("Unexpected error while confirming order")
        await state.clear()
        try:
            await callback.message.edit_text("❌ یه خطای غیرمنتظره پیش اومد. دوباره امتحان کن یا به پشتیبانی پیام بده.")
        except Exception:
            pass
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(success_text)
    await callback.answer()


# -------------------------------------------------------- اطلاعات سفارش

@router.callback_query(F.data.startswith("order_info:"))
async def on_order_info(callback: CallbackQuery, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    order = await session.get(Order, order_id)
    if order is None:
        await callback.answer("سفارش پیدا نشد.", show_alert=True)
        return
    await callback.answer(
        f"وضعیت: {order.status}\nپیشرفت: {order.progress_count}/{order.target_count}",
        show_alert=True,
    )


# ------------------------------------------------------------ گزارش سفارش

@router.callback_query(F.data.startswith("report_order:"))
async def on_report_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    try:
        await bot.send_message(
            callback.from_user.id,
            f"📝 لطفاً مشکل سفارش شماره #{order_id} رو توضیح بده تا برای تیم بررسی ارسال شه:",
        )
        await redis_client.set(f"awaiting_report:{callback.from_user.id}", order_id, ex=600)
        await callback.answer("یه پیام خصوصی برات فرستادم، اونجا توضیح بده 👆", show_alert=True)
    except TelegramForbiddenError:
        await callback.answer("اول /start رو به ربات بزن، بعد دوباره گزارش بده.", show_alert=True)


class AwaitingReportFilter(BaseFilter):
    """فقط وقتی True برمی‌گردونه که کاربر منتظر فرستادن گزارش سفارش باشه؛
    در غیر این صورت False برمی‌گردونه و کنترل به هندلرهای بعدی (روترهای دیگه) می‌رسه."""

    async def __call__(self, message: Message) -> bool | dict:
        order_id = await redis_client.get(f"awaiting_report:{message.from_user.id}")
        if order_id is None:
            return False
        return {"report_order_id": int(order_id)}


@router.message(AwaitingReportFilter())
async def capture_report(message: Message, report_order_id: int, user: User, bot: Bot):
    await redis_client.delete(f"awaiting_report:{message.from_user.id}")
    text = (
        f"❗ <b>گزارش سفارش #{report_order_id}</b>\n"
        f"از: {user.full_name} (@{user.username or '-'} | {user.id})\n\n"
        f"{message.text or ''}"
    )
    try:
        await bot.send_message(cfg.OWNER_ID, text)
    except TelegramForbiddenError:
        pass
    await message.answer("✅ گزارشت ثبت و برای تیم ارسال شد.")

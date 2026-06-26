"""
سرویس سفارش - قلب پلتفرم (نسخه ۲):
1) اعتبارسنجی کانال/گروه (ربات باید ادمین با دسترسی لازم باشه)
2) تایید خودکار سفارش بدون دخالت دستی
3) فوروارد خودکار به کانال جمع‌آوری با فرمت کامل (توضیحات کانال + ۵ دکمه)
4) پاداش‌دهی به کسی که جوین می‌کنه + پورسانت رفرال از خرج خریدار
5) تشخیص لفت + ریفیل خودکار + جریمه‌ی لفت زودهنگام
"""
from datetime import datetime, timedelta
from html import escape as _esc

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    User, Channel, Order, Participation, OrderType, OrderStatus, ActionType,
)
from app.services.channel_service import get_or_create_channel
from app.services.wallet_service import add_diamonds, spend_diamonds, penalize
from app.services.settings_service import get_setting
from app.services.panel_service import get_user_rates
from app.services.vip_trust_service import adjust_trust, flag_fraud, is_rate_limited
from app.services.referral_service import reward_referral_if_eligible
from app.services.progression_service import progress_mission, check_achievements


class OrderError(Exception):
    pass


# ---------------------------------------------------------------- اعتبارسنجی

async def validate_channel_for_member_order(bot: Bot, chat_id: int) -> dict:
    """چک می‌کنه ربات توی کانال/گروه ادمینه و دسترسی دعوت/مدیریت داره"""
    try:
        chat = await bot.get_chat(chat_id)
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
    except TelegramBadRequest as e:
        return {"ok": False, "error": f"دسترسی به کانال/گروه ممکن نشد: {e.message}"}

    if member.status != "administrator":
        return {"ok": False, "error": "ربات باید توی کانال یا گروه، ادمین باشه."}

    can_invite = getattr(member, "can_invite_users", False)
    can_manage = getattr(member, "can_manage_chat", False)
    if not (can_invite and can_manage):
        return {"ok": False, "error": "ربات نیاز به دسترسی «دعوت کاربران» و «مدیریت چت» داره."}

    return {
        "ok": True, "title": chat.title, "username": chat.username,
        "chat_id": chat.id, "description": getattr(chat, "description", None),
    }


# ---------------------------------------------------------------- ساخت سفارش

async def create_order(
    session: AsyncSession,
    bot: Bot,
    user: User,
    chat_id: int,
    target_count: int,
    sub_type: str | None = None,
) -> Order:
    if user.is_banned:
        raise OrderError("حساب شما مسدود است.")
    if user.trust_score < 20:
        raise OrderError("امتیاز اعتماد شما برای ثبت سفارش کافی نیست.")

    rates = await get_user_rates(session, user)
    active_count = (await session.execute(
        select(func.count(Order.id)).where(
            Order.user_id == user.id,
            Order.order_type == OrderType.MEMBER.value,
            Order.status.in_([OrderStatus.QUEUED.value, OrderStatus.IN_PROGRESS.value, OrderStatus.REFILLING.value]),
        )
    )).scalar_one()
    if active_count >= rates["max_active_orders"]:
        raise OrderError(f"حداکثر {rates['max_active_orders']} سفارش فعال هم‌زمان می‌تونی داشته باشی.")

    check = await validate_channel_for_member_order(bot, chat_id)
    if not check["ok"]:
        raise OrderError(check["error"])

    channel = await get_or_create_channel(
        session, check["chat_id"], check.get("username"), check.get("title"), user.id,
        description=check.get("description"),
    )
    if channel.is_banned:
        raise OrderError("این کانال/گروه مسدود شده و نمی‌تونه سفارش بگیره.")

    if not channel.username and not channel.invite_link:
        try:
            link = await bot.create_chat_invite_link(channel.chat_id)
            channel.invite_link = link.invite_link
        except TelegramBadRequest:
            pass

    dup = await session.execute(
        select(Order).where(
            Order.channel_id == channel.id,
            Order.order_type == OrderType.MEMBER.value,
            Order.status.in_([OrderStatus.QUEUED.value, OrderStatus.IN_PROGRESS.value, OrderStatus.REFILLING.value]),
        )
    )
    if dup.scalar_one_or_none():
        raise OrderError("یک سفارش فعال روی این کانال/گروه داری. اول بگذار تکمیل شه.")

    price_per_unit = await get_setting(session, "price_per_member", settings.PRICE_PER_MEMBER)
    price_total = int(price_per_unit * target_count)

    ok = await spend_diamonds(session, user, price_total, ActionType.ORDER_PAYMENT, meta=f"member:{channel.chat_id}")
    if not ok:
        raise OrderError(f"موجودی استارز کافی نیست. هزینه‌ی این سفارش {price_total} ⭐ است.")

    if user.referred_by:
        referrer = await session.get(User, user.referred_by)
        if referrer and not referrer.is_banned:
            rates = await get_user_rates(session, referrer)
            percent = rates["referral_percent"]
            if percent > 0:
                commission = int(price_total * percent / 100)
                if commission > 0:
                    await add_diamonds(session, referrer, commission, ActionType.COMMISSION, meta=f"from:{user.id}")

    order = Order(
        user_id=user.id,
        channel_id=channel.id,
        order_type=OrderType.MEMBER.value,
        sub_type=sub_type,
        target_count=target_count,
        price_total=price_total,
        status=OrderStatus.QUEUED.value,
    )
    session.add(order)
    await session.flush()
    return order


# ---------------------------------------------------------- فوروارد به کانال

async def _build_collector_text(order: Order, channel: Channel) -> str:
    brand = "استارز ممبر"
    link_part = f"@{channel.username}" if channel.username else channel.chat_id
    description = _esc(channel.description) if channel.description else "فاقد توضیحات"
    title = _esc(channel.title) if channel.title else "-"
    return (
        f"📢 سفارشات | {brand}\n\n"
        f"نام کانال‼️: {title}\n"
        f"📝 توضیحات کانال: {description}\n\n"
        f"ID: {link_part}"
    )


async def _build_collector_keyboard(bot: Bot, order: Order, channel: Channel) -> InlineKeyboardMarkup:
    me = await bot.get_me()
    join_url = (
        f"https://t.me/{channel.username}" if channel.username
        else (channel.invite_link or f"https://t.me/{me.username}")
    )
    enter_bot_url = f"https://t.me/{me.username}?start=fromchannel"

    remaining = max(order.target_count - order.progress_count, 0)
    title_text = f"《🚀 سفارش جدید | 👤 {remaining} ممبر 》"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=title_text, callback_data=f"order_info:{order.id}")],
        [
            InlineKeyboardButton(text="⭐ دریافت استارز", callback_data=f"join:{order.id}"),
            InlineKeyboardButton(text="🤤 عضویت ↗", url=join_url),
        ],
        [
            InlineKeyboardButton(text="❗ گزارش سفارش", callback_data=f"report_order:{order.id}"),
            InlineKeyboardButton(text="🤖 ورود به ربات", url=enter_bot_url),
        ],
    ])


async def post_order_to_collector(bot: Bot, session: AsyncSession, order: Order, channel: Channel):
    text = await _build_collector_text(order, channel)
    keyboard = await _build_collector_keyboard(bot, order, channel)
    message = await bot.send_message(settings.COLLECTOR_CHANNEL_ID, text, reply_markup=keyboard)
    order.collector_message_id = message.message_id
    order.status = OrderStatus.IN_PROGRESS.value
    await session.flush()


async def update_collector_message(bot: Bot, session: AsyncSession, order: Order, channel: Channel):
    if not order.collector_message_id:
        return

    if order.status == OrderStatus.COMPLETED.value:
        title = _esc(channel.title) if channel.title else "-"
        text = (
            f"✅ <b>سفارش تکمیل شد</b>\n\n"
            f"نام کانال: {title}\n"
            f"از همه‌ی شرکت‌کننده‌ها ممنونیم! ⭐"
        )
        try:
            await bot.edit_message_text(text, chat_id=settings.COLLECTOR_CHANNEL_ID, message_id=order.collector_message_id)
        except TelegramBadRequest:
            pass
        return

    text = await _build_collector_text(order, channel)
    keyboard = await _build_collector_keyboard(bot, order, channel)
    try:
        await bot.edit_message_text(
            text, chat_id=settings.COLLECTOR_CHANNEL_ID, message_id=order.collector_message_id,
            reply_markup=keyboard,
        )
    except TelegramBadRequest:
        pass


# ------------------------------------------------------------- کلیک کاربر

async def handle_collector_click(session: AsyncSession, bot: Bot, order_id: int, clicker: User) -> dict:
    order = await session.get(Order, order_id)
    if order is None:
        return {"ok": False, "message": "این سفارش پیدا نشد."}
    if order.status not in (OrderStatus.IN_PROGRESS.value, OrderStatus.REFILLING.value):
        return {"ok": False, "message": "این سفارش دیگه فعال نیست."}
    if clicker.is_banned:
        return {"ok": False, "message": "حساب شما مسدود است."}
    if clicker.id == order.user_id:
        await flag_fraud(session, clicker, "self_join_attempt", details=str(order.id), trust_penalty=3)
        return {"ok": False, "message": "نمی‌تونی توی سفارش خودت جایزه بگیری 🙂"}

    existing = await session.execute(
        select(Participation).where(Participation.order_id == order.id, Participation.user_id == clicker.id)
    )
    if existing.scalar_one_or_none():
        return {"ok": False, "message": "قبلاً جایزه‌ی این سفارش رو گرفتی."}

    if await is_rate_limited(clicker.id, "join_click", max_count=20, window_seconds=60):
        await flag_fraud(session, clicker, "rapid_join_rate", trust_penalty=5)
        return {"ok": False, "message": "سرعتت زیاده! چند ثانیه صبر کن."}

    channel = await session.get(Channel, order.channel_id)

    try:
        member = await bot.get_chat_member(channel.chat_id, clicker.id)
    except TelegramBadRequest:
        return {"ok": False, "message": "اول باید عضو کانال/گروه بشی، بعد دکمه رو بزن."}
    if member.status not in ("member", "administrator", "creator"):
        return {"ok": False, "message": "اول باید عضو کانال/گروه بشی، بعد دکمه رو بزن."}

    rates = await get_user_rates(session, clicker)
    reward = rates["join_reward"]

    await add_diamonds(session, clicker, reward, ActionType.JOIN_REWARD, meta=f"order:{order.id}")
    session.add(Participation(order_id=order.id, user_id=clicker.id, rewarded=True, reward_amount=reward))

    clicker.joins_today += 1
    await progress_mission(session, clicker, "join_channels", increment=1)
    await reward_referral_if_eligible(session, bot, clicker.id)
    await check_achievements(session, clicker)

    completed = False
    order.progress_count += 1
    if order.progress_count >= order.target_count:
        order.status = OrderStatus.COMPLETED.value
        order.completed_at = datetime.utcnow()
        guarantee_days = await get_setting(session, "guarantee_days", settings.GUARANTEE_DAYS)
        order.guarantee_until = datetime.utcnow() + timedelta(days=guarantee_days)
        owner = await session.get(User, order.user_id)
        if owner:
            owner.orders_completed_count += 1
            await check_achievements(session, owner)
        completed = True

    await session.flush()
    await update_collector_message(bot, session, order, channel)

    return {"ok": True, "message": f"🎉 {reward} ⭐ به کیفت اضافه شد!", "completed": completed}


# --------------------------------------------------------------- لفت/ریفیل

async def handle_member_left(session: AsyncSession, bot: Bot, channel_chat_id: int, left_user_id: int):
    """وقتی یوزری از کانالی که توش سفارش گارانتی‌دار داره لفت میده، این صدا زده میشه"""
    result = await session.execute(select(Channel).where(Channel.chat_id == channel_chat_id))
    channel = result.scalar_one_or_none()
    if channel is None:
        return

    now = datetime.utcnow()
    orders = await session.execute(
        select(Order).where(
            Order.channel_id == channel.id,
            Order.order_type == OrderType.MEMBER.value,
            Order.status.in_([OrderStatus.COMPLETED.value, OrderStatus.IN_PROGRESS.value, OrderStatus.REFILLING.value]),
            Order.guarantee_until.is_not(None),
            Order.guarantee_until >= now,
        )
    )
    orders = orders.scalars().all()
    if not orders:
        return

    leave_penalty_days = await get_setting(session, "leave_penalty_days", 4)

    for order in orders:
        participation = await session.execute(
            select(Participation).where(
                Participation.order_id == order.id,
                Participation.user_id == left_user_id,
                Participation.left_at.is_(None),
            )
        )
        participation = participation.scalar_one_or_none()
        if participation is None:
            continue

        participation.left_at = now
        left_user = await session.get(User, left_user_id)
        if left_user:
            left_user.leaves_count += 1
            await adjust_trust(session, left_user, -5)

            days_since_join = (now - participation.joined_at).days
            if days_since_join < leave_penalty_days:
                await penalize(
                    session, left_user, participation.reward_amount, ActionType.LEAVE_PENALTY,
                    meta=f"order:{order.id}",
                )

        order.progress_count = max(order.progress_count - 1, 0)
        order.refill_count += 1
        order.status = OrderStatus.REFILLING.value

        await session.flush()
        await update_collector_message(bot, session, order, channel)

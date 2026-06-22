"""
سرویس سفارش - قلب پلتفرم:
1) اعتبارسنجی کانال (ربات باید ادمین با دسترسی لازم باشه - فقط برای سفارش ممبر)
2) تایید خودکار سفارش بدون دخالت دستی
3) فوروارد خودکار به کانال جمع‌آوری
4) پاداش‌دهی به کسی که جوین/بازدید می‌کنه
5) تشخیص لفت + ریفیل خودکار در دوره گارانتی
"""
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    User, Channel, Order, Participation, OrderType, OrderStatus, ActionType,
)
from app.services.channel_service import get_or_create_channel
from app.services.wallet_service import add_diamonds, spend_diamonds
from app.services.settings_service import get_setting
from app.services.vip_trust_service import (
    get_reward_multiplier, adjust_trust, flag_fraud, is_rate_limited,
)
from app.services.referral_service import reward_referral_if_eligible
from app.services.progression_service import progress_mission, check_achievements


class OrderError(Exception):
    pass


# ---------------------------------------------------------------- اعتبارسنجی

async def validate_channel_for_member_order(bot: Bot, chat_id: int) -> dict:
    """چک می‌کنه ربات توی کانال ادمینه و دسترسی دعوت/مدیریت داره"""
    try:
        chat = await bot.get_chat(chat_id)
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
    except TelegramBadRequest as e:
        return {"ok": False, "error": f"دسترسی به کانال ممکن نشد: {e.message}"}

    if member.status != "administrator":
        return {"ok": False, "error": "ربات باید توی کانال، ادمین باشه."}

    can_invite = getattr(member, "can_invite_users", False)
    can_manage = getattr(member, "can_manage_chat", False)
    if not (can_invite and can_manage):
        return {"ok": False, "error": "ربات نیاز به دسترسی «دعوت کاربران» و «مدیریت چت» داره."}

    return {"ok": True, "title": chat.title, "username": chat.username, "chat_id": chat.id}


async def validate_channel_for_ad_order(bot: Bot, chat_id: int) -> dict:
    try:
        chat = await bot.get_chat(chat_id)
    except TelegramBadRequest as e:
        return {"ok": False, "error": f"دسترسی به کانال ممکن نشد: {e.message}"}
    return {"ok": True, "title": chat.title, "username": chat.username, "chat_id": chat.id}


# ---------------------------------------------------------------- ساخت سفارش

async def create_order(
    session: AsyncSession,
    bot: Bot,
    user: User,
    chat_id: int,
    order_type: OrderType,
    target_count: int,
    sub_type: str | None = None,
) -> Order:
    if user.is_banned:
        raise OrderError("حساب شما مسدود است.")
    if user.trust_score < 20:
        raise OrderError("امتیاز اعتماد شما برای ثبت سفارش کافی نیست.")

    if order_type == OrderType.MEMBER:
        check = await validate_channel_for_member_order(bot, chat_id)
    else:
        check = await validate_channel_for_ad_order(bot, chat_id)

    if not check["ok"]:
        raise OrderError(check["error"])

    channel = await get_or_create_channel(
        session, check["chat_id"], check.get("username"), check.get("title"), user.id
    )
    if channel.is_banned:
        raise OrderError("این کانال مسدود شده و نمی‌تونه سفارش بگیره.")

    # جلوگیری از سفارش تکراری فعال روی همون کانال و همون نوع
    dup = await session.execute(
        select(Order).where(
            Order.channel_id == channel.id,
            Order.order_type == order_type.value,
            Order.status.in_([OrderStatus.QUEUED.value, OrderStatus.IN_PROGRESS.value, OrderStatus.REFILLING.value]),
        )
    )
    if dup.scalar_one_or_none():
        raise OrderError("یک سفارش فعال از همین نوع روی این کانال داری. اول بگذار تکمیل شه.")

    if order_type == OrderType.MEMBER:
        price_per_unit = await get_setting(session, "price_per_member", settings.PRICE_PER_MEMBER)
    else:
        price_per_unit = await get_setting(session, "price_per_ad_hour", settings.PRICE_PER_AD_HOUR)

    price_total = int(price_per_unit * target_count)

    ok = await spend_diamonds(session, user, price_total, ActionType.ORDER_PAYMENT, meta=f"{order_type.value}:{channel.chat_id}")
    if not ok:
        raise OrderError(f"موجودی الماس کافی نیست. هزینه‌ی این سفارش {price_total} 💎 است.")

    order = Order(
        user_id=user.id,
        channel_id=channel.id,
        order_type=order_type.value,
        sub_type=sub_type,
        target_count=target_count,
        price_total=price_total,
        status=OrderStatus.QUEUED.value,
    )
    session.add(order)
    await session.flush()
    return order


# ---------------------------------------------------------- فوروارد به کانال

def _build_collector_keyboard(order: Order, reward: int) -> InlineKeyboardMarkup:
    if order.order_type == OrderType.MEMBER.value:
        text = f"🚀 جوین شو و {reward} 💎 بگیر"
    else:
        text = f"👀 مشاهده کن و {reward} 💎 بگیر"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"join:{order.id}")]])


async def post_order_to_collector(bot: Bot, session: AsyncSession, order: Order, channel: Channel):
    join_reward = await get_setting(session, "join_reward", settings.DEFAULT_JOIN_REWARD)

    link = f"@{channel.username}" if channel.username else channel.title or str(channel.chat_id)
    if order.order_type == OrderType.MEMBER.value:
        remaining = max(order.target_count - order.progress_count, 0)
        caption = (
            f"📢 <b>سفارش جدید ممبر</b>\n\n"
            f"کانال: {link}\n"
            f"باقی‌مانده: {remaining} نفر\n\n"
            f"با جوین شدن، {join_reward} 💎 فوری بگیر!"
        )
    else:
        caption = (
            f"📣 <b>تبلیغ کانال</b>\n\n"
            f"کانال: {link}\n"
            f"به مدت {order.target_count} ساعت در حال نمایش\n\n"
            f"با مشاهده، {join_reward} 💎 فوری بگیر!"
        )

    message = await bot.send_message(
        settings.COLLECTOR_CHANNEL_ID, caption, reply_markup=_build_collector_keyboard(order, join_reward)
    )
    order.collector_message_id = message.message_id
    order.status = OrderStatus.IN_PROGRESS.value
    await session.flush()


async def update_collector_message(bot: Bot, session: AsyncSession, order: Order, channel: Channel, extra_note: str = ""):
    if not order.collector_message_id:
        return
    join_reward = await get_setting(session, "join_reward", settings.DEFAULT_JOIN_REWARD)
    link = f"@{channel.username}" if channel.username else channel.title or str(channel.chat_id)

    if order.status == OrderStatus.COMPLETED.value:
        text = f"✅ <b>سفارش تکمیل شد</b>\n\nکانال: {link}\nاز همه‌ی شرکت‌کننده‌ها ممنونیم! 💎"
        try:
            await bot.edit_message_text(text, chat_id=settings.COLLECTOR_CHANNEL_ID, message_id=order.collector_message_id)
        except TelegramBadRequest:
            pass
        return

    remaining = max(order.target_count - order.progress_count, 0)
    text = (
        f"📢 <b>سفارش ممبر</b> {extra_note}\n\n"
        f"کانال: {link}\n"
        f"باقی‌مانده: {remaining} نفر\n\n"
        f"با جوین شدن، {join_reward} 💎 فوری بگیر!"
    )
    try:
        await bot.edit_message_text(
            text, chat_id=settings.COLLECTOR_CHANNEL_ID, message_id=order.collector_message_id,
            reply_markup=_build_collector_keyboard(order, join_reward),
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

    if order.order_type == OrderType.MEMBER.value:
        try:
            member = await bot.get_chat_member(channel.chat_id, clicker.id)
        except TelegramBadRequest:
            return {"ok": False, "message": "اول باید عضو کانال بشی، بعد دکمه رو بزن."}
        if member.status not in ("member", "administrator", "creator"):
            return {"ok": False, "message": "اول باید عضو کانال بشی، بعد دکمه رو بزن."}

    base_reward = await get_setting(session, "join_reward", settings.DEFAULT_JOIN_REWARD)
    multiplier = await get_reward_multiplier(session, clicker)
    reward = int(base_reward * multiplier)

    await add_diamonds(session, clicker, reward, ActionType.JOIN_REWARD, meta=f"order:{order.id}")
    session.add(Participation(order_id=order.id, user_id=clicker.id, rewarded=True, reward_amount=reward))

    clicker.joins_today += 1
    await progress_mission(session, clicker, "join_channels", increment=1)
    await reward_referral_if_eligible(session, clicker.id)
    await check_achievements(session, clicker)

    completed = False
    if order.order_type == OrderType.MEMBER.value:
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

    return {"ok": True, "message": f"🎉 {reward} 💎 به کیفت اضافه شد!", "completed": completed}


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

        order.progress_count = max(order.progress_count - 1, 0)
        order.refill_count += 1
        order.status = OrderStatus.REFILLING.value

        await session.flush()
        await update_collector_message(bot, session, order, channel, extra_note="(🔄 نیاز به ریفیل)")

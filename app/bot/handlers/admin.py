"""پنل مدیریت کامل برای اونر/ادمین - بدون دخالت کد، همه از داخل ربات"""
import random
import string
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Order, Wallet, Ticket, TicketStatus, GiftCode, BroadcastJob, ActionType
from app.bot.keyboards import admin_panel_keyboard
from app.services.settings_service import set_setting, get_setting
from app.services.wallet_service import add_diamonds, spend_diamonds

router = Router(name="admin")
router.message.filter(F.from_user.id == settings.OWNER_ID)
router.callback_query.filter(F.from_user.id == settings.OWNER_ID)


class GiftCodeStates(StatesGroup):
    waiting_amount = State()
    waiting_max_uses = State()


class BroadcastStates(StatesGroup):
    waiting_text = State()


@router.message(F.text == "🛠 پنل مدیریت")
async def admin_home(message: Message):
    await message.answer("🛠 <b>پنل مدیریت</b>", reply_markup=admin_panel_keyboard())


@router.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    users_count = (await session.execute(select(func.count(User.id)))).scalar_one()
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar_one()
    diamonds_in_circulation = (await session.execute(select(func.coalesce(func.sum(Wallet.diamonds), 0)))).scalar_one()
    open_tickets = (await session.execute(select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN.value))).scalar_one()

    await callback.message.edit_text(
        f"📊 <b>آمار کلی پلتفرم</b>\n\n"
        f"👤 کاربران: {users_count}\n"
        f"🧾 سفارش‌ها: {orders_count}\n"
        f"💎 الماس در گردش: {diamonds_in_circulation}\n"
        f"🎫 تیکت‌های باز: {open_tickets}",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:giftcode")
async def admin_giftcode_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiftCodeStates.waiting_amount)
    await callback.message.edit_text("چند الماس این گیفت‌کد بده؟ (عدد بفرست)")
    await callback.answer()


@router.message(GiftCodeStates.waiting_amount)
async def admin_giftcode_amount(message: Message, state: FSMContext):
    if not (message.text or "").strip().isdigit():
        await message.answer("فقط عدد بفرست.")
        return
    await state.update_data(amount=int(message.text.strip()))
    await state.set_state(GiftCodeStates.waiting_max_uses)
    await message.answer("این کد چندبار قابل استفاده باشه؟ (عدد بفرست)")


@router.message(GiftCodeStates.waiting_max_uses)
async def admin_giftcode_uses(message: Message, state: FSMContext, session: AsyncSession):
    if not (message.text or "").strip().isdigit():
        await message.answer("فقط عدد بفرست.")
        return

    data = await state.get_data()
    await state.clear()

    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    gift = GiftCode(
        code=code, amount=data["amount"], max_uses=int(message.text.strip()),
        created_by=message.from_user.id, expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(gift)
    await session.flush()

    await message.answer(f"✅ کد ساخته شد:\n\n<code>{code}</code>\n\nمقدار: {data['amount']} 💎 | تعداد استفاده: {gift.max_uses}")


@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_text)
    await callback.message.edit_text("متن پیامی که می‌خوای برای همه‌ی کاربران ارسال شه رو بفرست:")
    await callback.answer()


@router.message(BroadcastStates.waiting_text)
async def admin_broadcast_text(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    job = BroadcastJob(created_by=message.from_user.id, target_segment="all", text=message.text or "")
    session.add(job)
    await session.flush()

    try:
        from app.tasks.broadcast_tasks import send_broadcast
        send_broadcast.delay(job.id)
        await message.answer(f"✅ بردکاست #{job.id} به صف ارسال اضافه شد.")
    except Exception:
        await message.answer("⚠️ صف Celery در دسترس نیست؛ بردکاست ذخیره شد ولی ارسال نشد.")


@router.callback_query(F.data == "adm:settings")
async def admin_settings(callback: CallbackQuery, session: AsyncSession):
    keys = ["join_reward", "referral_reward", "daily_reward", "price_per_member", "price_per_ad_hour", "guarantee_days"]
    defaults = {
        "join_reward": settings.DEFAULT_JOIN_REWARD, "referral_reward": settings.DEFAULT_REFERRAL_REWARD,
        "daily_reward": 5, "price_per_member": settings.PRICE_PER_MEMBER,
        "price_per_ad_hour": settings.PRICE_PER_AD_HOUR, "guarantee_days": settings.GUARANTEE_DAYS,
    }
    lines = ["⚙️ <b>تنظیمات فعلی اقتصاد</b>\n"]
    for k in keys:
        v = await get_setting(session, k, defaults[k])
        lines.append(f"<code>{k}</code> = {v}")
    lines.append("\nبرای تغییر:\n<code>/setconfig کلید مقدار</code>\nمثلا: <code>/setconfig join_reward 15</code>")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())
    await callback.answer()


@router.message(Command("setconfig"))
async def cmd_setconfig(message: Message, command: CommandObject, session: AsyncSession):
    if not command.args:
        await message.answer("فرمت درست: /setconfig کلید مقدار")
        return
    parts = command.args.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("فرمت درست: /setconfig کلید مقدار")
        return
    key, value = parts
    await set_setting(session, key, value)
    await message.answer(f"✅ {key} = {value} ذخیره شد.")


@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject, session: AsyncSession):
    if not command.args:
        await message.answer("فرمت: /ban آیدی_عددی [دلیل]")
        return
    parts = command.args.split(maxsplit=1)
    try:
        target = await session.get(User, int(parts[0]))
    except ValueError:
        await message.answer("آیدی عددی نامعتبره.")
        return
    if not target:
        await message.answer("کاربر پیدا نشد.")
        return
    target.is_banned = True
    target.ban_reason = parts[1] if len(parts) > 1 else None
    await message.answer(f"🚫 کاربر {target.id} مسدود شد.")


@router.message(Command("unban"))
async def cmd_unban(message: Message, command: CommandObject, session: AsyncSession):
    if not command.args:
        await message.answer("فرمت: /unban آیدی_عددی")
        return
    try:
        target = await session.get(User, int(command.args.strip()))
    except ValueError:
        await message.answer("آیدی عددی نامعتبره.")
        return
    if not target:
        await message.answer("کاربر پیدا نشد.")
        return
    target.is_banned = False
    target.ban_reason = None
    await message.answer(f"✅ کاربر {target.id} آنبن شد.")


@router.message(Command("adjustwallet"))
async def cmd_adjust_wallet(message: Message, command: CommandObject, session: AsyncSession):
    """واریز یا برداشت دستی الماس - مقدار منفی برای برداشت"""
    if not command.args:
        await message.answer("فرمت: /adjustwallet آیدی_عددی مقدار")
        return
    parts = command.args.split()
    if len(parts) != 2:
        await message.answer("فرمت: /adjustwallet آیدی_عددی مقدار")
        return
    try:
        target = await session.get(User, int(parts[0]))
        amount = int(parts[1])
    except ValueError:
        await message.answer("ورودی نامعتبره. هر دو مقدار باید عدد باشن.")
        return
    if not target:
        await message.answer("کاربر پیدا نشد.")
        return
    if amount >= 0:
        await add_diamonds(session, target, amount, ActionType.ADMIN_ADJUST, meta=f"by:{message.from_user.id}")
    else:
        await spend_diamonds(session, target, -amount, ActionType.ADMIN_ADJUST, meta=f"by:{message.from_user.id}")
    await message.answer(f"✅ موجودی کاربر {target.id} به‌روز شد.")

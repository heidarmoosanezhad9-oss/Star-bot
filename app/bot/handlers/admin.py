"""پنل مدیریت کامل برای اونر/ادمین - بدون دخالت کد، همه از داخل ربات"""
import random
import string
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    User, Order, Wallet, Ticket, TicketStatus, GiftCode, BroadcastJob, ActionType,
    PanelTier, PanelPrice, StarPackage, PurchaseRequest, PurchaseStatus,
    ForceSubChannel, ForceSubJoin, CustomButton, AdminUser, AdminRole, Mission,
)
from app.bot.keyboards import admin_panel_keyboard
from app.services.settings_service import set_setting, get_setting
from app.services.wallet_service import add_diamonds, spend_diamonds
from app.services.admin_service import can_manage_settings, can_handle_support, add_admin, remove_admin
from app.services.custom_button_service import create_button, delete_button, list_active_buttons

router = Router(name="admin")


async def _require_full(message: Message, session: AsyncSession) -> bool:
    if not await can_manage_settings(session, message.from_user.id):
        await message.answer("⛔️ دسترسی نداری.")
        return False
    return True


async def _require_support(message: Message, session: AsyncSession) -> bool:
    if not await can_handle_support(session, message.from_user.id):
        await message.answer("⛔️ دسترسی نداری.")
        return False
    return True


# ---------------------------------------------------------------- پنل اصلی

@router.message(F.text == "🛠 پنل مدیریت")
async def admin_home(message: Message, session: AsyncSession):
    if not await can_handle_support(session, message.from_user.id):
        return
    await message.answer("🛠 <b>پنل مدیریت</b>", reply_markup=admin_panel_keyboard())


@router.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    if not await can_handle_support(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    users_count = (await session.execute(select(func.count(User.id)))).scalar_one()
    verified_users_count = (await session.execute(
        select(func.count(func.distinct(ForceSubJoin.user_id)))
    )).scalar_one()
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar_one()
    stars_in_circulation = (await session.execute(select(func.coalesce(func.sum(Wallet.diamonds), 0)))).scalar_one()
    open_tickets = (await session.execute(select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN.value))).scalar_one()
    pending_purchases = (await session.execute(select(func.count(PurchaseRequest.id)).where(PurchaseRequest.status == PurchaseStatus.PENDING.value))).scalar_one()

    await callback.message.edit_text(
        f"📊 <b>آمار کلی پلتفرم</b>\n\n"
        f"👤 کل استارت‌زده‌ها: {users_count}\n"
        f"✅ کاربران واقعی (رد شده از گیت عضویت اجباری): {verified_users_count}\n"
        f"🧾 سفارش‌ها: {orders_count}\n"
        f"⭐ استارز در گردش: {stars_in_circulation}\n"
        f"🎫 تیکت‌های باز: {open_tickets}\n"
        f"🛍 خریدهای در انتظار: {pending_purchases}",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer()


# ------------------------------------------------------------ گیفت‌کد/بردکاست

class GiftCodeStates(StatesGroup):
    waiting_amount = State()
    waiting_max_uses = State()


@router.callback_query(F.data == "adm:giftcode")
async def admin_giftcode_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await can_manage_settings(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    await state.set_state(GiftCodeStates.waiting_amount)
    await callback.message.edit_text("چند استارز این گیفت‌کد بده؟ (عدد بفرست)")
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

    await message.answer(f"✅ کد ساخته شد:\n\n<code>{code}</code>\n\nمقدار: {data['amount']} ⭐ | تعداد استفاده: {gift.max_uses}")


class BroadcastStates(StatesGroup):
    waiting_text = State()


@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await can_manage_settings(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    await state.set_state(BroadcastStates.waiting_text)
    await callback.message.edit_text("متن پیامی که می‌خوای برای همه‌ی کاربران ارسال شه رو بفرست:")
    await callback.answer()


@router.message(BroadcastStates.waiting_text)
async def admin_broadcast_text(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    await state.clear()
    job = BroadcastJob(created_by=message.from_user.id, target_segment="all", text=message.text or "")
    session.add(job)
    await session.flush()

    progress_msg = await message.answer("⏳ در حال ارسال... (این پیام وقتی تموم شد آپدیت می‌شه)")

    from app.tasks.broadcast_tasks import send_broadcast_now
    result = await send_broadcast_now(session, bot, job)

    await progress_msg.edit_text(
        f"✅ بردکاست #{job.id} تموم شد.\n\n"
        f"📨 ارسال موفق: {result['sent']}\n"
        f"❌ ناموفق (مسدود/حذف‌شده و...): {result['failed']}\n"
        f"👥 از کل: {result['total']} کاربر"
    )


# --------------------------------------------------------------- تنظیمات

@router.callback_query(F.data == "adm:settings")
async def admin_settings(callback: CallbackQuery, session: AsyncSession):
    if not await can_manage_settings(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    keys = [
        "join_reward", "referral_reward", "daily_reward", "price_per_member",
        "price_per_ad_view", "guarantee_days", "leave_penalty_days",
        "sponsor_leave_penalty", "referral_min_joins",
    ]
    defaults = {
        "join_reward": settings.DEFAULT_JOIN_REWARD, "referral_reward": settings.DEFAULT_REFERRAL_REWARD,
        "daily_reward": 5, "price_per_member": settings.PRICE_PER_MEMBER,
        "price_per_ad_view": 1, "guarantee_days": settings.GUARANTEE_DAYS,
        "leave_penalty_days": 4, "sponsor_leave_penalty": 5, "referral_min_joins": 3,
    }
    lines = ["⚙️ <b>تنظیمات فعلی</b>\n"]
    for k in keys:
        v = await get_setting(session, k, defaults[k])
        lines.append(f"<code>{k}</code> = {v}")
    lines.append("\nبرای تغییر:\n<code>/setconfig کلید مقدار</code>")
    lines.append("\nبرای ویرایش متن‌ها (خوش‌آمد/قوانین/فروشگاه): <code>/edittext</code>")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())
    await callback.answer()


@router.message(Command("setconfig"))
async def cmd_setconfig(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
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


# --------------------------------------------------------------- ماموریت‌ها

@router.message(Command("listmissions"))
async def cmd_listmissions(message: Message, session: AsyncSession):
    if not await _require_full(message, session):
        return
    result = await session.execute(select(Mission))
    missions = result.scalars().all()
    lines = ["🎯 <b>ماموریت‌های فعلی</b>\n"]
    for m in missions:
        lines.append(
            f"<code>{m.code}</code> | {m.title} | هدف: {m.target_count} | پاداش: {m.reward_diamonds}⭐ "
            f"| {'فعال' if m.is_active else 'غیرفعال'}"
        )
    lines.append(
        "\nبرای ویرایش:\n<code>/editmission کد هدف پاداش</code>\n"
        "مثلا: <code>/editmission join_channels 10 50</code>"
    )
    await message.answer("\n".join(lines))


@router.message(Command("editmission"))
async def cmd_editmission(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    parts = (command.args or "").split()
    if len(parts) != 3:
        await message.answer("فرمت: /editmission کد هدف پاداش\nکدها رو با /listmissions ببین.")
        return
    code, target, reward = parts
    result = await session.execute(select(Mission).where(Mission.code == code))
    mission = result.scalar_one_or_none()
    if mission is None:
        await message.answer("این کد ماموریت پیدا نشد. با /listmissions کدهای درست رو ببین.")
        return
    try:
        mission.target_count = int(target)
        mission.reward_diamonds = int(reward)
    except ValueError:
        await message.answer("هدف و پاداش باید عدد باشن.")
        return
    await message.answer(f"✅ ماموریت «{mission.title}» آپدیت شد: هدف {mission.target_count} | پاداش {mission.reward_diamonds}⭐")


EDITABLE_TEXT_KEYS = ["welcome_text", "rules_text", "shop_intro_text", "shop_panel_intro_text", "shop_stars_intro_text"]


class EditTextStates(StatesGroup):
    waiting_text = State()


@router.message(Command("edittext"))
async def cmd_edittext(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession):
    if not await _require_full(message, session):
        return
    if not command.args:
        await message.answer("کلیدهای قابل ویرایش:\n" + "\n".join(f"<code>{k}</code>" for k in EDITABLE_TEXT_KEYS) +
                              "\n\nفرمت: <code>/edittext کلید</code>")
        return
    key = command.args.strip()
    if key not in EDITABLE_TEXT_KEYS:
        await message.answer("این کلید معتبر نیست.")
        return
    await state.set_state(EditTextStates.waiting_text)
    await state.update_data(text_key=key)
    await message.answer(f"متن جدید برای <code>{key}</code> رو بفرست (می‌تونه چندخطی باشه):")


@router.message(EditTextStates.waiting_text)
async def save_edited_text(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    await set_setting(session, data["text_key"], message.text or "")
    await message.answer(f"✅ متن <code>{data['text_key']}</code> ذخیره شد.")


# ----------------------------------------------------------- بن/کیف پول

@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
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
    if not await _require_full(message, session):
        return
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
    if not await _require_full(message, session):
        return
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
        await message.answer("ورودی نامعتبره.")
        return
    if not target:
        await message.answer("کاربر پیدا نشد.")
        return
    if amount >= 0:
        await add_diamonds(session, target, amount, ActionType.ADMIN_ADJUST, meta=f"by:{message.from_user.id}")
    else:
        await spend_diamonds(session, target, -amount, ActionType.ADMIN_ADJUST, meta=f"by:{message.from_user.id}")
    await message.answer(f"✅ موجودی کاربر {target.id} به‌روز شد.")


# -------------------------------------------------------------- مدیریت ادمین‌ها (فقط اونر)

@router.callback_query(F.data == "adm:admins")
async def admin_admins_panel(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("فقط اونر دسترسی داره.", show_alert=True)
        return
    result = await session.execute(select(AdminUser))
    admins = result.scalars().all()
    lines = ["👮 <b>ادمین‌های فعلی</b>\n"]
    if not admins:
        lines.append("کسی اضافه نشده.")
    for a in admins:
        lines.append(f"{a.user_id} - {a.role}")
    lines.append(
        "\nاضافه کردن: <code>/addadmin آیدی_عددی full|support</code>"
        "\nحذف کردن: <code>/removeadmin آیدی_عددی</code>"
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())
    await callback.answer()


@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message, command: CommandObject, session: AsyncSession):
    if message.from_user.id != settings.OWNER_ID:
        await message.answer("⛔️ فقط اونر می‌تونه ادمین اضافه کنه.")
        return
    if not command.args:
        await message.answer("فرمت: /addadmin آیدی_عددی full|support")
        return
    parts = command.args.split()
    if len(parts) != 2 or parts[1] not in (AdminRole.FULL.value, AdminRole.SUPPORT.value):
        await message.answer("فرمت: /addadmin آیدی_عددی full|support")
        return
    try:
        target_id = int(parts[0])
    except ValueError:
        await message.answer("آیدی عددی نامعتبره.")
        return
    await add_admin(session, target_id, parts[1], message.from_user.id)
    await message.answer(f"✅ کاربر {target_id} به‌عنوان ادمین «{parts[1]}» اضافه شد.")


@router.message(Command("removeadmin"))
async def cmd_removeadmin(message: Message, command: CommandObject, session: AsyncSession):
    if message.from_user.id != settings.OWNER_ID:
        await message.answer("⛔️ فقط اونر می‌تونه ادمین حذف کنه.")
        return
    if not command.args:
        await message.answer("فرمت: /removeadmin آیدی_عددی")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("آیدی عددی نامعتبره.")
        return
    removed = await remove_admin(session, target_id)
    await message.answer("✅ حذف شد." if removed else "این کاربر ادمین نبود.")


# ----------------------------------------------------------------- پنل‌ها

@router.callback_query(F.data == "adm:panels")
async def admin_panels_list(callback: CallbackQuery, session: AsyncSession):
    if not await can_manage_settings(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    result = await session.execute(select(PanelTier))
    tiers = result.scalars().all()
    lines = ["🥇 <b>پنل‌های فعلی</b>\n"]
    for t in tiers:
        prices_result = await session.execute(select(PanelPrice).where(PanelPrice.panel_tier_id == t.id))
        prices = prices_result.scalars().all()
        price_str = " | ".join(f"{p.duration_days}روزه:{p.price_label}(#{p.id})" for p in prices) or "بدون قیمت"
        lines.append(f"#{t.id} {t.emoji} {t.name} | جوین:{t.join_reward}⭐ رفرال:{t.referral_reward}⭐ پورسانت:{t.referral_percent}%\n{price_str}")
    lines.append(
        "\n➕ پنل جدید: <code>/addpanel نام ایموجی جوین رفرال پورسانت حداکثرسفارش</code>"
        "\n➕ قیمت جدید: <code>/addpanelprice آیدی_پنل تعداد_روز برچسب_قیمت</code>"
        "\n🗑 حذف پنل: <code>/delpanel آیدی_پنل</code>"
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())
    await callback.answer()


@router.message(Command("addpanel"))
async def cmd_addpanel(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    parts = (command.args or "").split()
    if len(parts) != 6:
        await message.answer("فرمت: /addpanel نام ایموجی جوین رفرال پورسانت حداکثرسفارش")
        return
    name, emoji, join_r, ref_r, percent, max_orders = parts
    try:
        tier = PanelTier(
            name=name, emoji=emoji, join_reward=int(join_r), referral_reward=int(ref_r),
            referral_percent=int(percent), max_active_orders=int(max_orders),
        )
    except ValueError:
        await message.answer("مقادیر عددی نامعتبرن.")
        return
    session.add(tier)
    await session.flush()
    await message.answer(f"✅ پنل #{tier.id} ساخته شد. حالا با /addpanelprice برای قیمتش اضافه کن.")


@router.message(Command("addpanelprice"))
async def cmd_addpanelprice(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    parts = (command.args or "").split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("فرمت: /addpanelprice آیدی_پنل تعداد_روز برچسب_قیمت")
        return
    try:
        panel_id = int(parts[0])
        days = int(parts[1])
    except ValueError:
        await message.answer("آیدی پنل و تعداد روز باید عدد باشن.")
        return
    tier = await session.get(PanelTier, panel_id)
    if not tier:
        await message.answer("پنل پیدا نشد.")
        return
    price = PanelPrice(panel_tier_id=panel_id, duration_days=days, price_label=parts[2])
    session.add(price)
    await session.flush()
    await message.answer(f"✅ قیمت #{price.id} برای پنل {tier.name} اضافه شد.")


@router.message(Command("delpanel"))
async def cmd_delpanel(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    try:
        tier = await session.get(PanelTier, int((command.args or "").strip()))
    except ValueError:
        tier = None
    if not tier:
        await message.answer("پنل پیدا نشد.")
        return
    tier.is_active = False
    await message.answer("✅ پنل غیرفعال شد.")


# --------------------------------------------------------------- بسته استارز

@router.message(Command("addstarpkg"))
async def cmd_addstarpkg(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("فرمت: /addstarpkg تعداد_استارز برچسب_قیمت")
        return
    try:
        amount = int(parts[0])
    except ValueError:
        await message.answer("تعداد استارز باید عدد باشه.")
        return
    pkg = StarPackage(amount_stars=amount, price_label=parts[1])
    session.add(pkg)
    await session.flush()
    await message.answer(f"✅ بسته #{pkg.id} ({amount} ⭐) ساخته شد.")


@router.message(Command("delstarpkg"))
async def cmd_delstarpkg(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    try:
        pkg = await session.get(StarPackage, int((command.args or "").strip()))
    except ValueError:
        pkg = None
    if not pkg:
        await message.answer("بسته پیدا نشد.")
        return
    pkg.is_active = False
    await message.answer("✅ بسته غیرفعال شد.")


# --------------------------------------------------------------- عضویت اجباری

@router.callback_query(F.data == "adm:forcesub")
async def admin_forcesub_list(callback: CallbackQuery, session: AsyncSession):
    if not await can_manage_settings(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    result = await session.execute(select(ForceSubChannel))
    channels = result.scalars().all()
    lines = ["🔒 <b>کانال/گروه‌های عضویت اجباری</b>\n"]
    for c in channels:
        lines.append(f"#{c.id} {c.title or c.chat_id} {'✅' if c.is_active else '❌'}")
    lines.append(
        "\n➕ اضافه کردن: <code>/addforcesub لینک_یا_یوزرنیم_یا_آیدی</code> (ربات باید قبلش عضو/ادمین اونجا باشه)"
        "\n🗑 حذف: <code>/delforcesub آیدی</code>"
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())
    await callback.answer()


def _parse_chat_ref(text: str) -> str | int:
    """ورودی addforcesub رو از حالت لینک/یوزرنیم/آیدی به فرمتی که bot.get_chat می‌فهمه تبدیل می‌کنه"""
    text = text.strip()
    if "t.me/" in text:
        text = text.split("t.me/")[-1].split("?")[0].strip("/")
        if text.startswith("+") or text.startswith("joinchat"):
            return text  # لینک دعوت خصوصی - احتمالا resolve نمیشه، پیام خطا توضیح می‌ده
    if text.lstrip("-").isdigit():
        return int(text)
    if not text.startswith("@"):
        text = "@" + text
    return text


@router.message(Command("addforcesub"))
async def cmd_addforcesub(message: Message, command: CommandObject, session: AsyncSession, bot: Bot):
    if not await _require_full(message, session):
        return
    if not command.args:
        await message.answer("فرمت: /addforcesub لینک_یا_یوزرنیم_یا_آیدی_عددی")
        return

    chat_ref = _parse_chat_ref(command.args)
    try:
        chat = await bot.get_chat(chat_ref)
    except TelegramBadRequest as e:
        await message.answer(
            f"❌ پیدا نشد: {e.message}\n\n"
            "اگه کانال/گروه یوزرنیم عمومی ندارد (لینک دعوت خصوصیه)، باید آیدی عددیش رو بدی: "
            "یه پیام از همون کانال/گروه رو به @JsonDumpBot فوروارد کن تا آیدی عددی (شروع‌شده با -100) رو بگیری، "
            "بعد همون رو با /addforcesub بفرست."
        )
        return
    except Exception as e:
        await message.answer(f"خطا: {e}")
        return

    fs = ForceSubChannel(chat_id=chat.id, title=chat.title, username=chat.username)
    session.add(fs)
    await session.flush()
    await message.answer(f"✅ {chat.title} به لیست عضویت اجباری اضافه شد.")


@router.message(Command("delforcesub"))
async def cmd_delforcesub(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    try:
        fs = await session.get(ForceSubChannel, int((command.args or "").strip()))
    except ValueError:
        fs = None
    if not fs:
        await message.answer("پیدا نشد.")
        return
    fs.is_active = False
    await message.answer("✅ غیرفعال شد.")


# --------------------------------------------------------------- دکمه سفارشی

class AddButtonStates(StatesGroup):
    waiting_label = State()
    waiting_response = State()


@router.callback_query(F.data == "adm:buttons")
async def admin_buttons_list(callback: CallbackQuery, session: AsyncSession):
    if not await can_manage_settings(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    buttons = await list_active_buttons(session)
    lines = ["🧩 <b>دکمه‌های سفارشی</b>\n"]
    for b in buttons:
        lines.append(f"«{b.label}»")
    lines.append("\n➕ ساخت دکمه جدید: <code>/addbutton</code>\n🗑 حذف: <code>/delbutton متن_دکمه</code>")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())
    await callback.answer()


@router.message(Command("addbutton"))
async def cmd_addbutton(message: Message, state: FSMContext, session: AsyncSession):
    if not await _require_full(message, session):
        return
    await state.set_state(AddButtonStates.waiting_label)
    await message.answer("متن دکمه رو بفرست (همینی که توی منو نشون داده می‌شه):")


@router.message(AddButtonStates.waiting_label)
async def addbutton_label(message: Message, state: FSMContext):
    await state.update_data(label=(message.text or "").strip())
    await state.set_state(AddButtonStates.waiting_response)
    await message.answer("حالا متنی که با زدن این دکمه نشون داده می‌شه رو بفرست:")


@router.message(AddButtonStates.waiting_response)
async def addbutton_response(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    await create_button(session, data["label"], message.text or "")
    await message.answer(f"✅ دکمه «{data['label']}» ساخته شد و توی منو ظاهر می‌شه.")


@router.message(Command("delbutton"))
async def cmd_delbutton(message: Message, command: CommandObject, session: AsyncSession):
    if not await _require_full(message, session):
        return
    if not command.args:
        await message.answer("فرمت: /delbutton متن_دکمه")
        return
    removed = await delete_button(session, command.args.strip())
    await message.answer("✅ حذف شد." if removed else "پیدا نشد.")


# ------------------------------------------------------------- خریدهای در انتظار

@router.callback_query(F.data == "adm:purchases")
async def admin_purchases_list(callback: CallbackQuery, session: AsyncSession):
    if not await can_handle_support(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    result = await session.execute(
        select(PurchaseRequest).where(PurchaseRequest.status == PurchaseStatus.PENDING.value)
    )
    requests = result.scalars().all()
    if not requests:
        await callback.message.edit_text("هیچ خرید در انتظاری نیست.", reply_markup=admin_panel_keyboard())
        await callback.answer()
        return

    lines = ["🛍 <b>خریدهای در انتظار</b>\n"]
    buttons = []
    for r in requests:
        lines.append(f"#{r.id} - {r.request_type} - کاربر {r.user_id}")
        buttons.append([
            InlineKeyboardButton(text=f"✅ تایید #{r.id}", callback_data=f"approve_purchase:{r.id}"),
            InlineKeyboardButton(text=f"❌ رد #{r.id}", callback_data=f"reject_purchase:{r.id}"),
        ])
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


# ----------------------------------------------------------------- تیکت‌ها

@router.callback_query(F.data == "adm:tickets")
async def admin_tickets_list(callback: CallbackQuery, session: AsyncSession):
    if not await can_handle_support(session, callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    result = await session.execute(select(Ticket).where(Ticket.status == TicketStatus.OPEN.value).limit(10))
    tickets = result.scalars().all()
    lines = ["🎫 <b>تیکت‌های باز</b>\n"]
    for t in tickets:
        lines.append(f"#{t.id} - {t.subject} (کاربر {t.user_id})")
    if not tickets:
        lines.append("تیکت بازی نیست.")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())
    await callback.answer()

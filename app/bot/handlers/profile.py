"""هندلر پروفایل کاربر: موجودی، پنل، تراست‌اسکور، سفارش‌های خودش"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Order, Wallet
from app.services.wallet_service import get_or_create_wallet
from app.services.panel_service import get_active_panel

router = Router(name="profile")


def _leaderboard_keyboard(active: str) -> InlineKeyboardMarkup:
    coins_label = "⭐ برترین‌های سکه ✅" if active == "coins" else "⭐ برترین‌های سکه"
    ref_label = "👥 برترین‌های رفرال ✅" if active == "referrals" else "👥 برترین‌های رفرال"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=coins_label, callback_data="lb:coins"),
        InlineKeyboardButton(text=ref_label, callback_data="lb:referrals"),
    ]])


async def _leaderboard_text(session: AsyncSession, kind: str) -> str:
    medals = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
    if kind == "referrals":
        result = await session.execute(
            select(User).where(User.referrals_count > 0).order_by(desc(User.referrals_count)).limit(10)
        )
        rows = result.scalars().all()
        lines = ["👥 <b>برترین کاربران بر اساس تعداد زیرمجموعه</b>\n"]
        if not rows:
            lines.append("هنوز کسی زیرمجموعه‌ای نگرفته.")
        for i, u in enumerate(rows):
            name = u.full_name or (f"@{u.username}" if u.username else f"کاربر {u.id}")
            lines.append(f"{medals[i]} {name} — {u.referrals_count} زیرمجموعه")
        return "\n".join(lines)
    else:
        result = await session.execute(
            select(User, Wallet.diamonds)
            .join(Wallet, Wallet.user_id == User.id)
            .where(Wallet.diamonds > 0)
            .order_by(desc(Wallet.diamonds))
            .limit(10)
        )
        rows = result.all()
        lines = ["⭐ <b>برترین کاربران بر اساس موجودی استارز</b>\n"]
        if not rows:
            lines.append("هنوز کسی استارزی جمع نکرده.")
        for i, (u, diamonds) in enumerate(rows):
            name = u.full_name or (f"@{u.username}" if u.username else f"کاربر {u.id}")
            lines.append(f"{medals[i]} {name} — {diamonds} ⭐")
        return "\n".join(lines)


@router.message(F.text == "🏆 برترین کاربران")
async def show_leaderboard(message: Message, session: AsyncSession):
    text = await _leaderboard_text(session, "coins")
    await message.answer(text, reply_markup=_leaderboard_keyboard("coins"))


@router.callback_query(F.data.startswith("lb:"))
async def switch_leaderboard(callback: CallbackQuery, session: AsyncSession):
    kind = callback.data.split(":")[1]
    text = await _leaderboard_text(session, kind)
    await callback.message.edit_text(text, reply_markup=_leaderboard_keyboard(kind))
    await callback.answer()


@router.message(F.text == "👤 پروفایل من")
async def show_profile(message: Message, session: AsyncSession, user: User):
    panel = await get_active_panel(session, user)
    if panel:
        panel_text = f"{panel.emoji} {panel.name} (تا {user.panel_expires_at.strftime('%Y-%m-%d')})"
    else:
        panel_text = "بدون پنل (رایگان)"

    wallet = await get_or_create_wallet(session, user.id)
    text = (
        f"👤 <b>پروفایل تو</b>\n\n"
        f"⭐ موجودی استارز: {wallet.diamonds}\n"
        f"🥇 پنل فعلی: {panel_text}\n"
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

"""هندلر رفرال + کد هدیه + نمایش ماموریت روزانه"""
from datetime import date

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, GiftCode, GiftCodeRedemption, Mission, UserMissionProgress, ActionType
from app.services.wallet_service import add_diamonds
from app.services.settings_service import get_setting

router = Router(name="extras")


class GiftCodeStates(StatesGroup):
    waiting_code = State()


@router.message(F.text == "👥 زیرمجموعه‌گیری")
async def referral_info(message: Message, session: AsyncSession, user: User, bot: Bot):
    me = await bot.get_me()
    min_joins = await get_setting(session, "referral_min_joins", 3)
    link = f"https://t.me/{me.username}?start=ref_{user.id}"
    await message.answer(
        f"👥 <b>زیرمجموعه‌گیری</b>\n\n"
        f"لینک دعوت تو:\n{link}\n\n"
        f"تعداد زیرمجموعه فعلی: {user.referrals_count}\n"
        f"⚠️ هر زیرمجموعه باید حداقل {min_joins} کانال از کانال سفارش‌ها عضو شه تا برات استارز بیاد."
    )


@router.message(F.text == "🎯 ماموریت روزانه")
async def daily_missions(message: Message, session: AsyncSession, user: User):
    result = await session.execute(select(Mission).where(Mission.is_active == True))  # noqa: E712
    missions = result.scalars().all()
    if not missions:
        await message.answer("فعلاً ماموریتی تعریف نشده.")
        return

    lines = ["🎯 <b>ماموریت‌های امروز</b>\n"]
    for m in missions:
        prog_result = await session.execute(
            select(UserMissionProgress).where(
                UserMissionProgress.user_id == user.id,
                UserMissionProgress.mission_id == m.id,
                UserMissionProgress.reset_date == date.today(),
            )
        )
        progress = prog_result.scalar_one_or_none()
        current = progress.progress if progress else 0
        done = "✅" if (progress and progress.completed) else "⏳"
        lines.append(f"{done} {m.title}: {min(current, m.target_count)}/{m.target_count} (+{m.reward_diamonds}⭐)")

    await message.answer("\n".join(lines))


@router.message(F.text == "🎁 کد هدیه")
async def ask_gift_code(message: Message, state: FSMContext):
    await state.set_state(GiftCodeStates.waiting_code)
    await message.answer("کد هدیه‌ت رو بفرست:")


@router.message(GiftCodeStates.waiting_code)
async def redeem_gift_code(message: Message, state: FSMContext, session: AsyncSession, user: User):
    code_text = (message.text or "").strip().upper()
    await state.clear()

    result = await session.execute(select(GiftCode).where(GiftCode.code == code_text, GiftCode.is_active == True))  # noqa: E712
    gift = result.scalar_one_or_none()

    if gift is None:
        await message.answer("❌ این کد معتبر نیست.")
        return
    if gift.expires_at and gift.expires_at < message.date.replace(tzinfo=None):
        await message.answer("❌ تاریخ این کد گذشته.")
        return
    if gift.used_count >= gift.max_uses:
        await message.answer("❌ ظرفیت این کد تموم شده.")
        return

    already = await session.execute(
        select(GiftCodeRedemption).where(GiftCodeRedemption.code_id == gift.id, GiftCodeRedemption.user_id == user.id)
    )
    if already.scalar_one_or_none():
        await message.answer("❌ قبلاً این کد رو استفاده کردی.")
        return

    await add_diamonds(session, user, gift.amount, ActionType.GIFT_CODE, meta=code_text)
    gift.used_count += 1
    session.add(GiftCodeRedemption(code_id=gift.id, user_id=user.id))

    await message.answer(f"🎉 کد فعال شد! {gift.amount} ⭐ به کیفت اضافه شد.")

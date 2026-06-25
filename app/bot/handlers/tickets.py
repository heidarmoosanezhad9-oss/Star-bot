"""هندلر تیکت پشتیبانی: کاربر پیام می‌فرسته، برای اونر فوروارد میشه، اونر با ریپلای جواب میده"""
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, Ticket, TicketMessage, TicketStatus
from app.redis_client import redis_client

router = Router(name="tickets")


class TicketStates(StatesGroup):
    waiting_message = State()


@router.message(F.text == "🎫 پشتیبانی")
async def start_ticket(message: Message, state: FSMContext):
    await state.set_state(TicketStates.waiting_message)
    await message.answer("سوال یا مشکلت رو بنویس، مستقیم به تیم پشتیبانی می‌فرستم:")


@router.message(TicketStates.waiting_message)
async def submit_ticket(message: Message, state: FSMContext, session: AsyncSession, user: User, bot: Bot):
    await state.clear()

    ticket = Ticket(user_id=user.id, subject=(message.text or "")[:80])
    session.add(ticket)
    await session.flush()

    session.add(TicketMessage(ticket_id=ticket.id, sender_id=user.id, is_admin=False, text=message.text or ""))
    await session.flush()

    forwarded = await bot.send_message(
        settings.OWNER_ID,
        f"🎫 <b>تیکت جدید #{ticket.id}</b>\n"
        f"از: {user.full_name} (@{user.username or '-'} | {user.id})\n\n"
        f"{message.text}\n\n"
        f"برای پاسخ، روی همین پیام ریپلای بزن.",
    )
    await redis_client.set(f"ticket_msg:{forwarded.message_id}", ticket.id, ex=60 * 60 * 24 * 30)

    await message.answer(f"✅ تیکت #{ticket.id} ثبت شد. به‌زودی جواب می‌گیری.")


@router.message(F.from_user.id == settings.OWNER_ID, F.reply_to_message)
async def admin_reply_ticket(message: Message, session: AsyncSession, bot: Bot):
    ticket_id = await redis_client.get(f"ticket_msg:{message.reply_to_message.message_id}")
    if ticket_id is None:
        return

    ticket = await session.get(Ticket, int(ticket_id))
    if ticket is None:
        return

    session.add(TicketMessage(ticket_id=ticket.id, sender_id=message.from_user.id, is_admin=True, text=message.text or ""))
    ticket.status = TicketStatus.ANSWERED.value
    await session.flush()

    await bot.send_message(ticket.user_id, f"📩 <b>پاسخ پشتیبانی (تیکت #{ticket.id})</b>\n\n{message.text}")
    await message.answer("✅ پاسخ ارسال شد.")

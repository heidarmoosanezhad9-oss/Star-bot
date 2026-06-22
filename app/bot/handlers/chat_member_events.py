"""
تشخیص لفت: تلگرام برای کانال‌هایی که ربات توشون ادمینه، رویداد chat_member می‌فرسته.
هر بار وضعیت یه عضو عوض شه (جوین/لفت/کیک)، اینجا چک می‌کنیم آیا روی سفارش گارانتی‌دار تاثیر داره.
"""
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_service import handle_member_left

router = Router(name="chat_member_events")

LEFT_STATUSES = {"left", "kicked"}
ACTIVE_STATUSES = {"member", "administrator", "creator", "restricted"}


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, session: AsyncSession, bot: Bot):
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    if old_status in ACTIVE_STATUSES and new_status in LEFT_STATUSES:
        await handle_member_left(session, bot, event.chat.id, event.new_chat_member.user.id)

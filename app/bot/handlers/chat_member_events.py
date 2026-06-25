"""
تشخیص لفت: تلگرام برای کانال‌هایی که ربات توشون ادمینه، رویداد chat_member می‌فرسته.
هم برای سفارش‌های گارانتی‌دار و هم برای کانال/گروه‌های عضویت اجباری چک می‌کنیم.
"""
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_service import handle_member_left
from app.services.force_sub_service import handle_force_sub_left

router = Router(name="chat_member_events")

LEFT_STATUSES = {"left", "kicked"}
ACTIVE_STATUSES = {"member", "administrator", "creator", "restricted"}


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, session: AsyncSession, bot: Bot):
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    if old_status in ACTIVE_STATUSES and new_status in LEFT_STATUSES:
        chat_id = event.chat.id
        user_id = event.new_chat_member.user.id
        await handle_member_left(session, bot, chat_id, user_id)
        await handle_force_sub_left(session, chat_id, user_id)

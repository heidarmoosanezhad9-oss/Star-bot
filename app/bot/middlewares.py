"""میدلورها: تزریق session دیتابیس، ساخت/آپدیت کاربر، و گیت عضویت اجباری"""
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.database import session_scope
from app.models import User, Wallet
from app.services.admin_service import is_admin_or_owner


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with session_scope() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data["session"]
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        user = await session.get(User, tg_user.id)
        if user is None:
            user = User(id=tg_user.id, username=tg_user.username, full_name=tg_user.full_name)
            session.add(user)
            await session.flush()
            session.add(Wallet(user_id=user.id))
            await session.flush()
        else:
            user.username = tg_user.username
            user.full_name = tg_user.full_name

        # هر پیام یا کلیک روی دکمه = یک تعامل واقعی؛ برای آمار "کاربر فعال" استفاده می‌شه
        user.last_active_at = datetime.utcnow()

        user.is_admin = await is_admin_or_owner(session, user.id)

        data["user"] = user
        return await handler(event, data)


class ForceSubMiddleware(BaseMiddleware):
    """قبل از پردازش هر پیام/دکمه‌ای، چک می‌کنه کاربر عضو کانال‌های اجباری شده یا نه"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user: User | None = data.get("user")
        if user is None or user.is_admin or user.is_banned:
            return await handler(event, data)

        from app.services.force_sub_service import get_missing_channels, build_force_sub_link

        session = data["session"]
        bot = data["bot"]
        missing = await get_missing_channels(bot, session, user)

        if not missing:
            return await handler(event, data)

        buttons = [[InlineKeyboardButton(text=f"📢 {ch.title or 'کانال'}", url=build_force_sub_link(ch))] for ch in missing]
        buttons.append([InlineKeyboardButton(text="✅ بررسی مجدد", callback_data="fs_check")])
        text = "🔒 برای استفاده از ربات، اول باید عضو کانال/گروه‌های زیر بشی:"

        if isinstance(event, CallbackQuery):
            try:
                await event.answer("هنوز عضو نشدی! لیست زیرو چک کن 👇", show_alert=True)
            except Exception:
                pass
            try:
                await bot.send_message(user.id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            except TelegramForbiddenError:
                pass  # کاربر هنوز /start نزده؛ همون alert بالا کافیه
        else:
            await event.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

        return  # متوقف کردن پردازش - هندلر اصلی صدا زده نمی‌شه

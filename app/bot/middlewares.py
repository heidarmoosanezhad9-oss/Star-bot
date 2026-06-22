"""میدلورها: تزریق session دیتابیس و get_or_create کاربر برای هر آپدیت"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.config import settings
from app.database import session_scope
from app.models import User, Wallet


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
            user = User(
                id=tg_user.id,
                username=tg_user.username,
                full_name=tg_user.full_name,
                is_admin=(tg_user.id == settings.OWNER_ID),
            )
            session.add(user)
            await session.flush()
            session.add(Wallet(user_id=user.id))
            await session.flush()
        else:
            user.username = tg_user.username
            user.full_name = tg_user.full_name
            if tg_user.id == settings.OWNER_ID:
                user.is_admin = True

        data["user"] = user
        return await handler(event, data)

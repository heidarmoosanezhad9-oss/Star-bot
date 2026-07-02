"""نقطه ورود اصلی ربات تلگرام"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config import settings
from app.database import init_models, session_scope
from app.seed import seed_defaults
from app.bot.middlewares import DatabaseMiddleware, UserMiddleware, BanMiddleware, ForceSubMiddleware
from app.bot.handlers import (
    start, earn, orders, profile, referral, tickets, admin, chat_member_events,
    shop, rules, custom_content,
)

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    await init_models()  # برای پروداکشن واقعی از alembic استفاده کن (migrations/)
    async with session_scope() as session:
        await seed_defaults(session)

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)

    dp.update.outer_middleware(DatabaseMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    # این دوتا باید روی observer های اختصاصی ثبت شن، نه dp.update، تا event واقعا
    # از نوع Message/CallbackQuery باشه (نه خود شیء Update)
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
    dp.message.outer_middleware(ForceSubMiddleware())
    dp.callback_query.outer_middleware(ForceSubMiddleware())

    # ترتیب مهمه: روترهای دارای فیلتر/FSM خاص اول، دکمه‌های سفارشی همیشه آخر
    dp.include_router(admin.router)
    dp.include_router(orders.router)
    dp.include_router(shop.router)
    dp.include_router(rules.router)
    dp.include_router(referral.router)
    dp.include_router(tickets.router)
    dp.include_router(earn.router)
    dp.include_router(profile.router)
    dp.include_router(start.router)
    dp.include_router(chat_member_events.router)
    dp.include_router(custom_content.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot starting polling...")
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"],
    )


if __name__ == "__main__":
    asyncio.run(main())

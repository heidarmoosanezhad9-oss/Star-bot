"""تسک ارسال بردکاست به کاربران (با فاصله‌ی امن برای جلوگیری از فلود/بن شدن ربات)"""
import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select

from app.config import settings
from app.database import session_scope
from app.models import User, BroadcastJob
from app.tasks.celery_app import celery_app


async def _send_broadcast(job_id: int):
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        async with session_scope() as session:
            job = await session.get(BroadcastJob, job_id)
            if job is None:
                return

            result = await session.execute(select(User.id).where(User.is_banned == False))  # noqa: E712
            user_ids = [row[0] for row in result.all()]

            sent = 0
            for uid in user_ids:
                try:
                    await bot.send_message(uid, job.text)
                    sent += 1
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except TelegramForbiddenError:
                    continue
                except Exception:
                    continue
                await asyncio.sleep(0.05)  # ~20 پیام در ثانیه، زیر سقف تلگرام

            job.sent_count = sent
            job.status = "done"
    finally:
        await bot.session.close()


@celery_app.task
def send_broadcast(job_id: int):
    asyncio.run(_send_broadcast(job_id))

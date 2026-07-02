"""
ارسال بردکاست. این تابع مستقیم (await) از هندلر ادمین صدا زده می‌شه - نه پشت‌صحنه،
نه با Celery - تا قابل‌پیش‌بینی و قابل‌دیباگ باشه.
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, BroadcastJob

logger = logging.getLogger(__name__)


async def send_broadcast_now(session: AsyncSession, bot: Bot, job: BroadcastJob) -> dict:
    """
    همون bot instance موجود رو استفاده می‌کنه (نه یه Bot جدید) تا هیچ مشکل
    raw session/event-loop ای پیش نیاد. مستقیم await می‌شه، پشت‌صحنه نمی‌فرسته.
    """
    logger.info(f"Broadcast job {job.id}: starting (sync mode)")

    result = await session.execute(select(User.id).where(User.is_banned == False))  # noqa: E712
    user_ids = [row[0] for row in result.all()]
    logger.info(f"Broadcast job {job.id}: {len(user_ids)} recipients")

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, job.text)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except TelegramForbiddenError:
            failed += 1
            continue
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast job {job.id}: failed to send to {uid}: {e!r}")
            continue
        await asyncio.sleep(0.05)

    job.sent_count = sent
    job.status = "done"
    await session.flush()
    logger.info(f"Broadcast job {job.id}: done, sent={sent}, failed={failed}")
    return {"sent": sent, "failed": failed, "total": len(user_ids)}

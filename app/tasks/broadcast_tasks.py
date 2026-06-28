"""تسک ارسال بردکاست به کاربران (با فاصله‌ی امن برای جلوگیری از فلود/بن شدن ربات)"""
import asyncio
import logging
import traceback

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select

from app.config import settings
from app.database import session_scope
from app.models import User, BroadcastJob
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _mark_failed(job_id: int, error_text: str):
    try:
        async with session_scope() as session:
            job = await session.get(BroadcastJob, job_id)
            if job:
                job.status = f"failed: {error_text}"[:250]
    except Exception:
        logger.exception("Even failed to mark broadcast job as failed")


async def _send_broadcast(job_id: int):
    logger.info(f"Broadcast job {job_id}: starting")
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        async with session_scope() as session:
            job = await session.get(BroadcastJob, job_id)
            if job is None:
                logger.warning(f"Broadcast job {job_id}: not found")
                return

            result = await session.execute(select(User.id).where(User.is_banned == False))  # noqa: E712
            user_ids = [row[0] for row in result.all()]
            logger.info(f"Broadcast job {job_id}: {len(user_ids)} recipients")

            sent = 0
            for uid in user_ids:
                try:
                    await bot.send_message(uid, job.text)
                    sent += 1
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except TelegramForbiddenError:
                    continue
                except BaseException as e:
                    logger.warning(f"Broadcast job {job_id}: failed to send to {uid}: {e!r}")
                    continue
                await asyncio.sleep(0.05)  # ~20 پیام در ثانیه، زیر سقف تلگرام

            job.sent_count = sent
            job.status = "done"
            logger.info(f"Broadcast job {job_id}: done, sent={sent}")
    except BaseException as e:
        logger.exception(f"Broadcast job {job_id}: CRASHED")
        await _mark_failed(job_id, f"{type(e).__name__}: {e}")
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass


@celery_app.task
def send_broadcast(job_id: int):
    asyncio.run(_send_broadcast(job_id))

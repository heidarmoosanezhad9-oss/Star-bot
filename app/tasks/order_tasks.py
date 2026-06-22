"""
تسک‌های دوره‌ای Celery:
1) recheck_active_member_orders: چک پشتیبان لفت (علاوه بر رویداد لحظه‌ای chat_member)
2) complete_expired_ad_orders: تبلیغاتی که زمانش تموم شده رو خودکار ببند
"""
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from app.config import settings
from app.database import session_scope
from app.models import Order, Channel, Participation, OrderType, OrderStatus
from app.services.order_service import handle_member_left, update_collector_message
from app.tasks.celery_app import celery_app

MAX_CHECKS_PER_RUN = 80


async def _recheck_active_member_orders():
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        async with session_scope() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(Order, Channel)
                .join(Channel, Channel.id == Order.channel_id)
                .where(
                    Order.order_type == OrderType.MEMBER.value,
                    Order.status.in_([OrderStatus.IN_PROGRESS.value, OrderStatus.REFILLING.value, OrderStatus.COMPLETED.value]),
                    Order.guarantee_until.is_not(None),
                    Order.guarantee_until >= now,
                )
            )
            orders = result.all()

            checked = 0
            for order, channel in orders:
                if checked >= MAX_CHECKS_PER_RUN:
                    break
                parts = await session.execute(
                    select(Participation).where(
                        Participation.order_id == order.id,
                        Participation.rewarded == True,  # noqa: E712
                        Participation.left_at.is_(None),
                    ).limit(10)
                )
                for p in parts.scalars().all():
                    if checked >= MAX_CHECKS_PER_RUN:
                        break
                    checked += 1
                    try:
                        member = await bot.get_chat_member(channel.chat_id, p.user_id)
                        if member.status not in ("member", "administrator", "creator"):
                            await handle_member_left(session, bot, channel.chat_id, p.user_id)
                    except TelegramBadRequest:
                        continue
                    await asyncio.sleep(0.1)  # احتیاط در برابر rate-limit تلگرام
    finally:
        await bot.session.close()


async def _complete_expired_ad_orders():
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        async with session_scope() as session:
            result = await session.execute(
                select(Order, Channel)
                .join(Channel, Channel.id == Order.channel_id)
                .where(Order.order_type == OrderType.ADVERTISING.value, Order.status == OrderStatus.IN_PROGRESS.value)
            )
            for order, channel in result.all():
                deadline = order.created_at + timedelta(hours=order.target_count)
                if datetime.utcnow() >= deadline:
                    order.status = OrderStatus.COMPLETED.value
                    order.completed_at = datetime.utcnow()
                    await session.flush()
                    await update_collector_message(bot, session, order, channel)
    finally:
        await bot.session.close()


@celery_app.task
def recheck_active_member_orders():
    asyncio.run(_recheck_active_member_orders())


@celery_app.task
def complete_expired_ad_orders():
    asyncio.run(_complete_expired_ad_orders())

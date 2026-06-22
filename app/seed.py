"""
دیتای اولیه‌ی پیشنهادی - همه از طریق ربات (/setconfig یا دستورات آینده) قابل تغییرن.
این فقط نقطه‌ی شروع منطقیه، نه مقدار قفل‌شده.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VIPLevel, Mission, Achievement


async def seed_defaults(session: AsyncSession):
    if (await session.execute(select(VIPLevel))).first() is None:
        session.add_all([
            VIPLevel(name="Bronze", min_total_earned=0, reward_multiplier=1.0, max_active_orders=2),
            VIPLevel(name="Silver", min_total_earned=500, reward_multiplier=1.1, max_active_orders=4),
            VIPLevel(name="Gold", min_total_earned=2000, reward_multiplier=1.25, max_active_orders=7, priority_support=True),
            VIPLevel(name="Diamond", min_total_earned=10000, reward_multiplier=1.5, max_active_orders=15, priority_support=True),
        ])

    if (await session.execute(select(Mission))).first() is None:
        session.add_all([
            Mission(code="join_channels", title="عضو ۵ کانال شو", target_count=5, reward_diamonds=20),
            Mission(code="invite_users", title="۲ نفر دعوت کن", target_count=2, reward_diamonds=30),
            Mission(code="stay_active", title="امروز فعال باش", target_count=1, reward_diamonds=5),
        ])

    if (await session.execute(select(Achievement))).first() is None:
        session.add_all([
            Achievement(code="first_order", title="اولین سفارش", target_field="orders_completed_count", target_value=1, reward_diamonds=50),
            Achievement(code="ten_referrals", title="۱۰ زیرمجموعه", target_field="referrals_count", target_value=10, reward_diamonds=200),
            Achievement(code="hundred_referrals", title="۱۰۰ زیرمجموعه", target_field="referrals_count", target_value=100, reward_diamonds=1500),
            Achievement(code="hundred_diamonds", title="۱۰۰ الماس کسب‌شده", target_field="total_diamonds_earned", target_value=100, reward_diamonds=20),
        ])

    await session.commit()

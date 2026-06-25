"""
دیتای اولیه‌ی پیشنهادی - همه از طریق ربات (پنل مدیریت) قابل تغییرن.
این فقط نقطه‌ی شروع منطقیه، نه مقدار قفل‌شده.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Mission, Achievement, PanelTier, PanelPrice, StarPackage


async def seed_defaults(session: AsyncSession):
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
            Achievement(code="hundred_diamonds", title="۱۰۰ استارز کسب‌شده", target_field="total_diamonds_earned", target_value=100, reward_diamonds=20),
        ])

    if (await session.execute(select(PanelTier))).first() is None:
        bronze = PanelTier(name="برنزی", emoji="🥉", join_reward=2, referral_reward=15, referral_percent=5, max_active_orders=2, sort_order=1)
        silver = PanelTier(name="حرفه‌ای", emoji="🥈", join_reward=3, referral_reward=20, referral_percent=10, max_active_orders=4, sort_order=2)
        gold = PanelTier(name="ویژه", emoji="🥇", join_reward=4, referral_reward=25, referral_percent=15, max_active_orders=8, sort_order=3)
        session.add_all([bronze, silver, gold])
        await session.flush()

        session.add_all([
            PanelPrice(panel_tier_id=silver.id, duration_days=15, price_label="۵۰ هزار تومن"),
            PanelPrice(panel_tier_id=gold.id, duration_days=15, price_label="۶۰ هزار تومن"),
            PanelPrice(panel_tier_id=silver.id, duration_days=30, price_label="۹۰ هزار تومن"),
            PanelPrice(panel_tier_id=gold.id, duration_days=30, price_label="۱۰۰ هزار تومن"),
        ])

    if (await session.execute(select(StarPackage))).first() is None:
        session.add_all([
            StarPackage(amount_stars=100, price_label="۲۰ هزار تومن", sort_order=1),
            StarPackage(amount_stars=250, price_label="۴۰ هزار تومن", sort_order=2),
            StarPackage(amount_stars=500, price_label="۶۰ هزار تومن", sort_order=3),
            StarPackage(amount_stars=1000, price_label="۱۰۰ هزار تومن", sort_order=4),
            StarPackage(amount_stars=4000, price_label="۴۰۰ هزار تومن", sort_order=5),
        ])

    await session.commit()

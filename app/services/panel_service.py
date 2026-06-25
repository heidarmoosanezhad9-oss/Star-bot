"""
سرویس پنل (جایگزین VIP خودکار قبلی):
کاربر با خریدن یک پنل (برنزی/حرفه‌ای/ویژه) به مدت معین، نرخ پاداش جوین/رفرال/پورسانت
مخصوص اون پنل رو می‌گیره. اگه پنل نداشته باشه یا منقضی شده باشه، نرخ‌های پایه (رایگان) اعمال می‌شه.
"""
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, PanelTier, PanelPrice
from app.services.settings_service import get_setting


async def get_active_panel(session: AsyncSession, user: User) -> PanelTier | None:
    if not user.active_panel_id:
        return None
    if not user.panel_expires_at or user.panel_expires_at < datetime.utcnow():
        return None
    return await session.get(PanelTier, user.active_panel_id)


async def get_user_rates(session: AsyncSession, user: User) -> dict:
    """برمی‌گردونه: join_reward, referral_reward, referral_percent, max_active_orders"""
    panel = await get_active_panel(session, user)
    if panel:
        return {
            "join_reward": panel.join_reward,
            "referral_reward": panel.referral_reward,
            "referral_percent": panel.referral_percent,
            "max_active_orders": panel.max_active_orders,
            "panel_name": f"{panel.emoji} {panel.name}",
        }

    base_join = await get_setting(session, "join_reward", settings.DEFAULT_JOIN_REWARD)
    base_referral = await get_setting(session, "referral_reward", settings.DEFAULT_REFERRAL_REWARD)
    return {
        "join_reward": base_join,
        "referral_reward": base_referral,
        "referral_percent": 0,
        "max_active_orders": 2,
        "panel_name": "رایگان",
    }


async def grant_panel(session: AsyncSession, user: User, panel_price: PanelPrice):
    """اعطای پنل بعد از تایید پرداخت توسط ادمین"""
    now = datetime.utcnow()
    # اگه پنل فعلی هنوز معتبره، مدت جدید رو بهش اضافه کن (تمدید)؛ وگرنه از امروز شروع کن
    base = user.panel_expires_at if (user.panel_expires_at and user.panel_expires_at > now) else now
    user.active_panel_id = panel_price.panel_tier_id
    user.panel_expires_at = base + timedelta(days=panel_price.duration_days)

"""سرویس نقش‌های ادمین - فقط اونر می‌تونه ادمین اضافه/حذف/رتبه‌بندی کنه"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AdminUser, AdminRole


async def get_admin_role(session: AsyncSession, user_id: int) -> str | None:
    """برمی‌گردونه: 'owner' / 'full' / 'support' / None (کاربر عادی)"""
    if user_id == settings.OWNER_ID:
        return "owner"
    admin = await session.get(AdminUser, user_id)
    return admin.role if admin else None


async def is_admin_or_owner(session: AsyncSession, user_id: int) -> bool:
    return (await get_admin_role(session, user_id)) is not None


async def can_manage_settings(session: AsyncSession, user_id: int) -> bool:
    """دسترسی کامل (تنظیمات/بردکاست/بن/پنل/دکمه‌ها) - فقط owner و full"""
    role = await get_admin_role(session, user_id)
    return role in ("owner", AdminRole.FULL.value)


async def can_handle_support(session: AsyncSession, user_id: int) -> bool:
    """دسترسی پشتیبانی (تیکت/تایید پرداخت) - همه‌ی ادمین‌ها"""
    role = await get_admin_role(session, user_id)
    return role is not None


async def add_admin(session: AsyncSession, user_id: int, role: str, granted_by: int):
    existing = await session.get(AdminUser, user_id)
    if existing:
        existing.role = role
        existing.granted_by = granted_by
    else:
        session.add(AdminUser(user_id=user_id, role=role, granted_by=granted_by))
    await session.flush()


async def remove_admin(session: AsyncSession, user_id: int):
    existing = await session.get(AdminUser, user_id)
    if existing:
        await session.delete(existing)
        await session.flush()
        return True
    return False

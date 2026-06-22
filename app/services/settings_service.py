"""
تنظیمات داینامیک: هر مقدار اقتصادی (پاداش‌ها/قیمت‌ها) اول از جدول settings در دیتابیس
خوانده می‌شه و اگه ست نشده بود، از .env به‌عنوان مقدار پیش‌فرض استفاده می‌شه.
این یعنی اونر می‌تونه بدون دیپلوی مجدد، مقادیر رو از داخل ربات تغییر بده.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Setting


async def get_setting(session: AsyncSession, key: str, default):
    row = await session.get(Setting, key)
    if row is None:
        return default
    # تشخیص نوع بر اساس مقدار پیش‌فرض
    if isinstance(default, bool):
        return row.value.lower() in ("1", "true", "yes")
    if isinstance(default, int):
        try:
            return int(row.value)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(row.value)
        except ValueError:
            return default
    return row.value


async def set_setting(session: AsyncSession, key: str, value, description: str | None = None):
    row = await session.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=str(value), description=description)
        session.add(row)
    else:
        row.value = str(value)
        if description:
            row.description = description
    await session.flush()
    return row

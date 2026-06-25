"""
اتصال async به PostgreSQL از طریق SQLAlchemy 2.0
"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    """برای استفاده در FastAPI (Depends)"""
    async with async_session() as session:
        yield session


@asynccontextmanager
async def session_scope():
    """برای استفاده در هندلرهای ربات و تسک‌های Celery"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models():
    """ساخت جدول‌ها (برای توسعه/تست سریع - در پروداکشن از alembic استفاده کن)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

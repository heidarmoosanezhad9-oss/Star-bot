"""مدل‌های رفرال، میشن روزانه و اچیومنت"""
from datetime import datetime, date

from sqlalchemy import BigInteger, String, Boolean, Integer, ForeignKey, DateTime, Date, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    referee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    reward_given: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)  # join_5_channels, invite_2_users, ...
    title: Mapped[str] = mapped_column(String(255))
    target_count: Mapped[int] = mapped_column(Integer)
    reward_diamonds: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_daily: Mapped[bool] = mapped_column(Boolean, default=True)


class UserMissionProgress(Base):
    __tablename__ = "user_mission_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    mission_id: Mapped[int] = mapped_column(Integer, ForeignKey("missions.id"))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    reset_date: Mapped[date] = mapped_column(Date, default=date.today)  # برای ریست روزانه


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    target_field: Mapped[str] = mapped_column(String(64))  # مثلا referrals_count
    target_value: Mapped[int] = mapped_column(Integer)
    reward_diamonds: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id"))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Event(Base):
    """رویداد فعال با ضریب پاداش بیشتر"""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

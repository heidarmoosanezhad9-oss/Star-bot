"""مدل‌های کانال، سفارش و مشارکت کاربران در سفارش‌ها"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, String, Boolean, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderType(str, enum.Enum):
    MEMBER = "member"
    ADVERTISING = "advertising"


class MemberSubType(str, enum.Enum):
    NORMAL = "normal"
    VIP = "vip"
    REAL = "real"
    IRANIAN = "iranian"
    INTERNATIONAL = "international"
    FAST = "fast"
    SLOW = "slow"


class OrderStatus(str, enum.Enum):
    PENDING_VALIDATION = "pending_validation"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REFILLING = "refilling"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)  # آیدی عددی کانال تلگرام
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"))

    order_type: Mapped[str] = mapped_column(String(16))
    sub_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # فقط برای ممبر

    target_count: Mapped[int] = mapped_column(Integer)  # تعداد ممبر هدف یا ساعت تبلیغ
    progress_count: Mapped[int] = mapped_column(Integer, default=0)

    price_total: Mapped[int] = mapped_column(Integer)  # به استارز
    status: Mapped[str] = mapped_column(String(24), default=OrderStatus.PENDING_VALIDATION.value)

    collector_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    refill_count: Mapped[int] = mapped_column(Integer, default=0)
    guarantee_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    channel: Mapped["Channel"] = relationship(lazy="selectin")


class Participation(Base):
    """ثبت اینکه کدوم کاربر برای کسب استارز وارد کانال کدوم سفارش شده"""
    __tablename__ = "participations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    reward_amount: Mapped[int] = mapped_column(Integer, default=0)
    refilled: Mapped[bool] = mapped_column(Boolean, default=False)  # یعنی جای این لفت رو یکی دیگه پر کرده

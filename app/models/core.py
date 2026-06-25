"""مدل‌های هسته: کاربر / کیف پول / تنظیمات داینامیک / لاگ‌ها"""
import enum
from datetime import datetime, date

from sqlalchemy import BigInteger, String, Boolean, Integer, ForeignKey, DateTime, Date, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="fa")

    referred_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # True فقط برای OWNER_ID (محاسبه در میدلور)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    trust_score: Mapped[int] = mapped_column(Integer, default=100)
    leaves_count: Mapped[int] = mapped_column(Integer, default=0)
    referrals_count: Mapped[int] = mapped_column(Integer, default=0)
    orders_completed_count: Mapped[int] = mapped_column(Integer, default=0)
    joins_today: Mapped[int] = mapped_column(Integer, default=0)

    total_diamonds_earned: Mapped[int] = mapped_column(Integer, default=0)  # کل استارز کسب‌شده در طول عمر (لاگ آماری)

    # --- پنل خریداری‌شده (جایگزین VIP خودکار قبلی) ---
    active_panel_id: Mapped[int | None] = mapped_column(ForeignKey("panel_tiers.id"), nullable=True)
    panel_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    last_daily_claim: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False, lazy="selectin")


class Wallet(Base):
    __tablename__ = "wallets"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    diamonds: Mapped[int] = mapped_column(Integer, default=0)  # نام داخلی ستون عوض نشد، نمایش = ⭐ استارز
    coins: Mapped[int] = mapped_column(Integer, default=0)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    gift_balance: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="wallet")


class Setting(Base):
    """تنظیمات و متن‌های قابل‌تغییر از پنل ادمین بدون نیاز به دیپلوی مجدد"""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # Text برای پشتیبانی متن‌های طولانی (قوانین و...)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ActionType(str, enum.Enum):
    JOIN_REWARD = "join_reward"
    REFERRAL_REWARD = "referral_reward"
    DAILY_REWARD = "daily_reward"
    MISSION_REWARD = "mission_reward"
    ACHIEVEMENT_REWARD = "achievement_reward"
    GIFT_CODE = "gift_code"
    ORDER_PAYMENT = "order_payment"
    ORDER_REFUND = "order_refund"
    ADMIN_ADJUST = "admin_adjust"
    LEAVE_PENALTY = "leave_penalty"
    SPONSOR_LEAVE_PENALTY = "sponsor_leave_penalty"
    PANEL_GRANT = "panel_grant"
    STAR_TOPUP = "star_topup"
    COMMISSION = "commission"


class WalletLog(Base):
    """رسید هر تغییر کیف پول - برای شفافیت کامل و حسابرسی"""
    __tablename__ = "wallet_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    action_type: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(Integer)  # می‌تونه منفی باشه
    balance_after: Mapped[int] = mapped_column(Integer)
    meta: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AdminLog(Base):
    """هر اقدام ادمین/اونر برای حسابرسی"""
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    flag_type: Mapped[str] = mapped_column(String(64))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

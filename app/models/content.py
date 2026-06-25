"""
مدل‌های فاز ۲:
- PanelTier / PanelPrice: سطوح پنل خریداری‌شده (جایگزین VIP خودکار قبلی)
- StarPackage / PurchaseRequest: فروشگاه و درخواست‌های پرداخت دستی
- CustomButton: دکمه‌های دلخواه اونر
- ForceSubChannel / ForceSubJoin: عضویت اجباری
- AdminUser: مدیریت ادمین‌ها با رتبه
- AdBanner: تبلیغ کانال به‌صورت بنر داخل بات (بر اساس تعداد نمایش)
"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, String, Boolean, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.orders import Channel


# ------------------------------------------------------------------ پنل‌ها

class PanelTier(Base):
    __tablename__ = "panel_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))          # برنزی / حرفه‌ای / ویژه
    emoji: Mapped[str] = mapped_column(String(8), default="🥉")
    join_reward: Mapped[int] = mapped_column(Integer)       # استارز هر جوین برای دارنده‌ی این پنل
    referral_reward: Mapped[int] = mapped_column(Integer)   # استارز هر زیرمجموعه
    referral_percent: Mapped[int] = mapped_column(Integer, default=0)  # درصد پورسانت از خرج زیرمجموعه
    max_active_orders: Mapped[int] = mapped_column(Integer, default=3)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PanelPrice(Base):
    """هر پنل می‌تونه چند مدت/قیمت مختلف داشته باشه (مثلا ۱۵ روزه و ۳۰ روزه)"""
    __tablename__ = "panel_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panel_tier_id: Mapped[int] = mapped_column(Integer, ForeignKey("panel_tiers.id"))
    duration_days: Mapped[int] = mapped_column(Integer)
    price_label: Mapped[str] = mapped_column(String(64))   # متن آزاد قیمت، مثلا "۵۰ هزار تومن"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    panel_tier: Mapped["PanelTier"] = relationship(lazy="selectin")


class StarPackage(Base):
    __tablename__ = "star_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount_stars: Mapped[int] = mapped_column(Integer)
    price_label: Mapped[str] = mapped_column(String(64))   # مثلا "۲۰ هزار تومن"
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PurchaseStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    request_type: Mapped[str] = mapped_column(String(16))  # panel / stars
    panel_price_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("panel_prices.id"), nullable=True)
    star_package_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("star_packages.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=PurchaseStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    panel_price: Mapped["PanelPrice"] = relationship(lazy="selectin")
    star_package: Mapped["StarPackage"] = relationship(lazy="selectin")


# ------------------------------------------------------------- دکمه سفارشی

class CustomButton(Base):
    """دکمه‌ای که خود اونر از داخل ربات می‌سازه - بدون نیاز به کد"""
    __tablename__ = "custom_buttons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(64), unique=True)   # متن دکمه‌ی منو
    response_text: Mapped[str] = mapped_column(Text)               # پیامی که با زدنش نشون داده می‌شه
    buttons_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # دکمه‌های شیشه‌ای زیر پیام (JSON)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --------------------------------------------------------- عضویت اجباری

class ForceSubChannel(Base):
    __tablename__ = "force_sub_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ForceSubJoin(Base):
    """برای محاسبه‌ی جریمه‌ی لفت زود‌هنگام از کانال/گروه اسپانسر"""
    __tablename__ = "force_sub_joins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("force_sub_channels.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    penalized: Mapped[bool] = mapped_column(Boolean, default=False)


# -------------------------------------------------------------- ادمین‌ها

class AdminRole(str, enum.Enum):
    FULL = "full"        # همه‌چی جز مدیریت ادمین‌های دیگه
    SUPPORT = "support"  # فقط تیکت + تأیید پرداخت


class AdminUser(Base):
    __tablename__ = "admin_users"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), default=AdminRole.SUPPORT.value)
    granted_by: Mapped[int] = mapped_column(BigInteger)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --------------------------------------------------- تبلیغ بنر داخل بات

class AdBannerStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AdBanner(Base):
    """تبلیغ کانال - به‌جای پست توی کانال جمع‌آوری، داخل خود بات (منوی کسب استارز) نشون داده می‌شه"""
    __tablename__ = "ad_banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"))
    target_impressions: Mapped[int] = mapped_column(Integer)
    shown_count: Mapped[int] = mapped_column(Integer, default=0)
    price_total: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default=AdBannerStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    channel: Mapped["Channel"] = relationship(lazy="selectin")

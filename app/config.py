"""
کانفیگ مرکزی پروژه.
همه‌ی مقادیر از .env خوانده می‌شوند. هیچ مقدار حساسی هاردکد نشده است.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Telegram ---
    BOT_TOKEN: str
    OWNER_ID: int
    COLLECTOR_CHANNEL_ID: int

    # --- Database ---
    DATABASE_URL: str

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- اقتصاد پیش‌فرض (override از جدول Settings در دیتابیس هم ممکنه) ---
    DEFAULT_JOIN_REWARD: int = 10
    DEFAULT_REFERRAL_REWARD: int = 50
    DEFAULT_REFERRAL_PERCENT: int = 5
    GUARANTEE_DAYS: int = 15
    PRICE_PER_MEMBER: int = 2
    PRICE_PER_AD_HOUR: int = 20

    # --- متفرقه ---
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Tehran"
    COLLECTOR_CHANNEL_LINK: str = "https://t.me/stars_member_free"


settings = Settings()

"""اپ Celery + زمان‌بندی تسک‌های دوره‌ای (ریفیل/تشخیص لفت/تکمیل تبلیغ)"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "tgm",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.order_tasks", "app.tasks.broadcast_tasks"],
)

celery_app.conf.timezone = settings.TIMEZONE
celery_app.conf.beat_schedule = {
    "recheck-member-orders-every-15-min": {
        "task": "app.tasks.order_tasks.recheck_active_member_orders",
        "schedule": 15 * 60,
    },
    "complete-expired-ad-orders-every-10-min": {
        "task": "app.tasks.order_tasks.complete_expired_ad_orders",
        "schedule": 10 * 60,
    },
}

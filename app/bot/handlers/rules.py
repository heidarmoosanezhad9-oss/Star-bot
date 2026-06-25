"""هندلر نمایش قوانین - متن از جدول Settings خوانده می‌شه و توسط ادمین قابل‌ویرایشه"""
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.settings_service import get_setting

router = Router(name="rules")

DEFAULT_RULES = (
    "⛔️ به بخش قوانین استارز ممبر خوش آمدید.\n\n"
    "❗️ نکات مهم (با دقت بخوانید) ❗️:\n"
    "📍 وقتی توی سفارش‌ها عضو می‌شید و استارز می‌گیرین، نباید کمتر از ۴ روز لفت بدین "
    "وگرنه استارزش کسر می‌شه. روز پنجم می‌تونید لفت بدین.\n"
    "⚠️ ثبت سفارش کانال +۱۸ یا هر سرویس غیرقانونی باعث مسدود شدن همیشگی حساب و کانالتان می‌شود.\n"
    "⚠️ اگر سفارش در حال انجام دارید، آیدی مقصد رو تغییر ندید چون سفارشتون ناتمام می‌مونه.\n"
    "⚠️ به هیچ وجه پشت‌سرهم چند تا سفارش ندید.\n"
    "❌ از باگ‌های احتمالی ربات سوءاستفاده نکنید؛ کسانی که مسدود می‌شن بخشیده نمی‌شن.\n"
    "❗️ قبل از ثبت سفارش، ربات باید ادمین کانال یا گروهتون باشه.\n\n"
    "✅ کلیه‌ی پرداخت‌های کارت‌به‌کارت فقط توسط پشتیبانی ربات انجام می‌شه.\n"
    "جهت مشاوره یا خرید به پشتیبانی مراجعه کنید 👇"
)


@router.message(F.text == "📜 قوانین")
async def show_rules(message: Message, session: AsyncSession):
    text = await get_setting(session, "rules_text", DEFAULT_RULES)
    await message.answer(text)

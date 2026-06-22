"""هندلر شروع کار با ربات + ثبت رفرال از طریق دیپ‌لینک"""
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.bot.keyboards import main_menu
from app.services.referral_service import register_referral
from app.services.wallet_service import get_or_create_wallet

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User, bot: Bot):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_") and user.referred_by is None:
        try:
            referrer_id = int(parts[1].removeprefix("ref_"))
            await register_referral(session, user, referrer_id)
        except ValueError:
            pass

    wallet = await get_or_create_wallet(session, user.id)
    text = (
        f"سلام {message.from_user.first_name} 👋\n\n"
        "به پلتفرم رشد تلگرام خوش اومدی!\n"
        "از منوی پایین می‌تونی الماس جمع کنی، ممبر یا تبلیغ برای کانالت بخری، "
        "زیرمجموعه‌گیری کنی و خیلی کارای دیگه.\n\n"
        f"💎 موجودی فعلی: {wallet.diamonds}"
    )
    await message.answer(text, reply_markup=main_menu(is_admin=user.is_admin))


@router.message(F.text == "ℹ️ راهنما")
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>راهنمای سریع</b>\n\n"
        "💎 کسب الماس: عضو کانال‌ها بشو و الماس بگیر\n"
        "🛒 ثبت سفارش: برای کانال خودت ممبر یا تبلیغ بخر\n"
        "👥 زیرمجموعه‌گیری: لینک دعوتت رو بگیر و الماس اضافه کسب کن\n"
        "🎯 ماموریت روزانه: ماموریت‌های هرروز رو کامل کن\n"
        "🎁 کد هدیه: کد هدیه‌ت رو وارد کن\n"
        "🎫 پشتیبانی: هر سوالی داشتی بپرس"
    )

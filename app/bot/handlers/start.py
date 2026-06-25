"""هندلر شروع کار با ربات + ثبت رفرال از طریق دیپ‌لینک"""
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.bot.keyboards import main_menu
from app.services.referral_service import register_referral
from app.services.wallet_service import get_or_create_wallet
from app.services.custom_button_service import get_extra_labels
from app.services.settings_service import get_setting

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User, bot: Bot):
    parts = (message.text or "").split(maxsplit=1)
    new_referral = False
    if len(parts) > 1 and parts[1].startswith("ref_") and user.referred_by is None:
        try:
            referrer_id = int(parts[1].removeprefix("ref_"))
            if referrer_id != user.id:
                await register_referral(session, user, referrer_id)
                new_referral = True
        except ValueError:
            pass

    wallet = await get_or_create_wallet(session, user.id)
    welcome_text = await get_setting(
        session, "welcome_text",
        "سلام {name} 👋\n\nبه استارز ممبر خوش اومدی!\nاز منوی پایین می‌تونی استارز جمع کنی، "
        "ممبر یا تبلیغ برای کانالت بخری، زیرمجموعه‌گیری کنی و خیلی کارای دیگه."
    )
    text = welcome_text.format(name=message.from_user.first_name) + f"\n\n⭐ موجودی فعلی: {wallet.diamonds}"

    extra_labels = await get_extra_labels(session)
    await message.answer(text, reply_markup=main_menu(is_admin=user.is_admin, extra_labels=extra_labels))

    if new_referral:
        min_joins = await get_setting(session, "referral_min_joins", 3)
        await message.answer(
            f"🤝 یه دوست تو رو دعوت کرده!\n"
            f"برای اینکه اون هم پاداش بگیره، باید حداقل {min_joins} کانال از داخل کانال سفارش‌ها عضو شی و استارز بگیری."
        )


@router.callback_query(F.data == "fs_check")
async def on_force_sub_recheck(callback: CallbackQuery):
    # اگه به اینجا رسیده یعنی میدلور عضویت اجباری تاییدش کرده (وگرنه قبلش جلوش گرفته می‌شد)
    await callback.answer("✅ عضویتت تایید شد، می‌تونی ادامه بدی!", show_alert=True)
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.message(F.text == "ℹ️ راهنما")
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>راهنمای سریع</b>\n\n"
        "⭐ کسب استارز: عضو کانال‌ها بشو و استارز بگیر\n"
        "🛒 ثبت سفارش: برای کانال خودت ممبر یا تبلیغ بخر\n"
        "🛍 فروشگاه: خرید پنل یا استارز\n"
        "👥 زیرمجموعه‌گیری: لینک دعوتت رو بگیر\n"
        "🎯 ماموریت روزانه: ماموریت‌های هرروز رو کامل کن\n"
        "🎁 کد هدیه: کد هدیه‌ت رو وارد کن\n"
        "📜 قوانین: قبل از سفارش حتما بخون\n"
        "🎫 پشتیبانی: هر سوالی داشتی بپرس"
    )

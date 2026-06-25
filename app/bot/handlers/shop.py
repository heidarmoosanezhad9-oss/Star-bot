"""هندلر فروشگاه: خرید پنل یا استارز - پرداخت دستی، تأیید با یک تپ توسط ادمین"""
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, PanelTier, AdminUser
from app.services.shop_service import (
    list_panel_prices, list_star_packages, create_panel_purchase_request,
    create_star_purchase_request, approve_purchase, reject_purchase,
)
from app.services.settings_service import get_setting

router = Router(name="shop")

DEFAULT_SHOP_INTRO = "🛍 به فروشگاه استارز ممبر خوش آمدید☺️\n\nلطفا گزینه مورد نظر را جهت خرید انتخاب کنید👇"


async def _get_admin_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(AdminUser.user_id))
    ids = [row[0] for row in result.all()]
    return [settings.OWNER_ID] + ids


@router.message(F.text == "🛍 فروشگاه")
async def shop_main(message: Message, session: AsyncSession):
    text = await get_setting(session, "shop_intro_text", DEFAULT_SHOP_INTRO)
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥇 خرید پنل", callback_data="shop:panels")],
        [InlineKeyboardButton(text="⭐ خرید استارز", callback_data="shop:stars")],
    ]))


@router.callback_query(F.data == "shop:panels")
async def shop_panels(callback: CallbackQuery, session: AsyncSession):
    prices = await list_panel_prices(session)
    if not prices:
        await callback.answer("فعلاً پنلی برای فروش تعریف نشده.", show_alert=True)
        return

    intro = await get_setting(session, "shop_panel_intro_text", "♻ خرید پنل ♻\n\nیکی از گزینه‌های زیر رو انتخاب کن:")
    buttons = []
    for p in prices:
        tier: PanelTier = p.panel_tier
        buttons.append([InlineKeyboardButton(
            text=f"{tier.emoji} {tier.name} - {p.duration_days} روزه - {p.price_label}",
            callback_data=f"buyplan:{p.id}",
        )])
    await callback.message.edit_text(intro, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "shop:stars")
async def shop_stars(callback: CallbackQuery, session: AsyncSession):
    packages = await list_star_packages(session)
    if not packages:
        await callback.answer("فعلاً بسته‌ای برای فروش تعریف نشده.", show_alert=True)
        return

    intro = await get_setting(session, "shop_stars_intro_text", "💎 خرید استارز 💎\n\nیکی از بسته‌های زیر رو انتخاب کن:")
    buttons = [
        [InlineKeyboardButton(text=f"⭐ {pkg.amount_stars} - {pkg.price_label}", callback_data=f"buystars:{pkg.id}")]
        for pkg in packages
    ]
    await callback.message.edit_text(intro, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


async def _notify_admins_new_request(bot: Bot, session: AsyncSession, request_id: int, summary: str, buyer: User):
    admin_ids = await _get_admin_ids(session)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_purchase:{request_id}"),
        InlineKeyboardButton(text="❌ رد", callback_data=f"reject_purchase:{request_id}"),
    ]])
    text = (
        f"🛍 <b>درخواست خرید جدید #{request_id}</b>\n\n"
        f"خریدار: {buyer.full_name} (@{buyer.username or '-'} | {buyer.id})\n"
        f"{summary}\n\n"
        f"بعد از دریافت پرداخت، تایید کن:"
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb)
        except TelegramForbiddenError:
            continue


@router.callback_query(F.data.startswith("buyplan:"))
async def on_buy_plan(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot):
    price_id = int(callback.data.split(":")[1])
    req = await create_panel_purchase_request(session, user, price_id)
    await _notify_admins_new_request(bot, session, req.id, f"نوع: خرید پنل (#{price_id})", user)

    await callback.message.edit_text(
        f"✅ درخواستت ثبت شد (#{req.id}).\n\n"
        f"برای تکمیل خرید، رسید پرداخت رو به آیدی @{settings.ADMIN_CONTACT_USERNAME} بفرست.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="💬 پیام به ادمین", url=f"https://t.me/{settings.ADMIN_CONTACT_USERNAME}")
        ]]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buystars:"))
async def on_buy_stars(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot):
    package_id = int(callback.data.split(":")[1])
    req = await create_star_purchase_request(session, user, package_id)
    await _notify_admins_new_request(bot, session, req.id, f"نوع: خرید استارز (#{package_id})", user)

    await callback.message.edit_text(
        f"✅ درخواستت ثبت شد (#{req.id}).\n\n"
        f"برای تکمیل خرید، رسید پرداخت رو به آیدی @{settings.ADMIN_CONTACT_USERNAME} بفرست.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="💬 پیام به ادمین", url=f"https://t.me/{settings.ADMIN_CONTACT_USERNAME}")
        ]]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_purchase:"))
async def on_approve_purchase(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot):
    from app.services.admin_service import can_handle_support
    if not await can_handle_support(session, user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    request_id = int(callback.data.split(":")[1])
    result = await approve_purchase(session, bot, request_id, user.id)
    await callback.message.edit_text(callback.message.text + f"\n\n✅ تایید شد توسط {user.full_name}")
    await callback.answer(result, show_alert=True)


@router.callback_query(F.data.startswith("reject_purchase:"))
async def on_reject_purchase(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot):
    from app.services.admin_service import can_handle_support
    if not await can_handle_support(session, user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    request_id = int(callback.data.split(":")[1])
    result = await reject_purchase(session, bot, request_id, user.id)
    await callback.message.edit_text(callback.message.text + f"\n\n❌ رد شد توسط {user.full_name}")
    await callback.answer(result, show_alert=True)

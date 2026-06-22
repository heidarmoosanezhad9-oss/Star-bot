"""کیبوردهای منو اصلی و زیرمنوها"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="💎 کسب الماس"), KeyboardButton(text="🛒 ثبت سفارش")],
        [KeyboardButton(text="👤 پروفایل من"), KeyboardButton(text="👥 زیرمجموعه‌گیری")],
        [KeyboardButton(text="🎯 ماموریت روزانه"), KeyboardButton(text="🎁 کد هدیه")],
        [KeyboardButton(text="🎫 پشتیبانی")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🛠 پنل مدیریت")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def order_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 سفارش ممبر", callback_data="new_order:member")],
        [InlineKeyboardButton(text="📣 تبلیغ کانال", callback_data="new_order:advertising")],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ انصراف", callback_data="cancel")]])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید و پرداخت", callback_data=f"confirm:{action}")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel")],
    ])


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار کلی", callback_data="adm:stats")],
        [InlineKeyboardButton(text="📢 بردکاست", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="🎁 ساخت گیفت‌کد", callback_data="adm:giftcode")],
        [InlineKeyboardButton(text="⚙️ تنظیمات اقتصاد", callback_data="adm:settings")],
        [InlineKeyboardButton(text="🎫 تیکت‌های باز", callback_data="adm:tickets")],
    ])

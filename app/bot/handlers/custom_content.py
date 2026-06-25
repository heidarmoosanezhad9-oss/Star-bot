"""هندلر نمایش دکمه‌های سفارشی که اونر بدون کد ساخته - باید با کمترین اولویت رجیستر شه"""
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomButton
from app.services.custom_button_service import get_button_by_label, parse_buttons_json

router = Router(name="custom_content")


class IsCustomButtonFilter(BaseFilter):
    """فقط اگه متن پیام دقیقا با یکی از دکمه‌های سفارشی فعال یکی باشه True برمی‌گردونه"""

    async def __call__(self, message: Message, session: AsyncSession) -> bool | dict:
        if not message.text:
            return False
        btn = await get_button_by_label(session, message.text.strip())
        if btn is None:
            return False
        return {"custom_button": btn}


@router.message(IsCustomButtonFilter())
async def show_custom_button(message: Message, custom_button: CustomButton):
    buttons_data = parse_buttons_json(custom_button.buttons_json)
    keyboard = None
    if buttons_data:
        rows = []
        for item in buttons_data:
            if item.get("url"):
                rows.append([InlineKeyboardButton(text=item.get("label", "لینک"), url=item["url"])])
        if rows:
            keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    await message.answer(custom_button.response_text, reply_markup=keyboard)

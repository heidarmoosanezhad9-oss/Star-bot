"""سرویس دکمه‌های سفارشی - اونر/ادمین بدون کد دکمه می‌سازه"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomButton


async def list_active_buttons(session: AsyncSession) -> list[CustomButton]:
    result = await session.execute(
        select(CustomButton).where(CustomButton.is_active == True).order_by(CustomButton.sort_order)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_button_by_label(session: AsyncSession, label: str) -> CustomButton | None:
    result = await session.execute(
        select(CustomButton).where(CustomButton.label == label, CustomButton.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def create_button(session: AsyncSession, label: str, response_text: str, buttons: list[dict] | None = None) -> CustomButton:
    btn = CustomButton(
        label=label, response_text=response_text,
        buttons_json=json.dumps(buttons, ensure_ascii=False) if buttons else None,
    )
    session.add(btn)
    await session.flush()
    return btn


async def delete_button(session: AsyncSession, label: str) -> bool:
    btn = await get_button_by_label(session, label)
    if btn is None:
        return False
    await session.delete(btn)
    await session.flush()
    return True


async def get_extra_labels(session: AsyncSession) -> list[str]:
    buttons = await list_active_buttons(session)
    return [b.label for b in buttons]


def parse_buttons_json(buttons_json: str | None) -> list[dict]:
    if not buttons_json:
        return []
    try:
        return json.loads(buttons_json)
    except (json.JSONDecodeError, TypeError):
        return []

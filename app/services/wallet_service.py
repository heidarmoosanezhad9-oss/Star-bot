"""سرویس کیف پول: واریز/برداشت استارز با لاگ کامل برای حسابرسی"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Wallet, WalletLog, ActionType


async def get_or_create_wallet(session: AsyncSession, user_id: int) -> Wallet:
    wallet = await session.get(Wallet, user_id)
    if wallet is None:
        wallet = Wallet(user_id=user_id)
        session.add(wallet)
        await session.flush()
    return wallet


async def add_diamonds(
    session: AsyncSession,
    user: User,
    amount: int,
    action_type: ActionType,
    meta: str | None = None,
) -> int:
    """واریز استارز به کاربر. amount باید مثبت باشه. برمی‌گردونه موجودی جدید."""
    if amount <= 0:
        return (await get_or_create_wallet(session, user.id)).diamonds

    wallet = await get_or_create_wallet(session, user.id)
    wallet.diamonds += amount
    user.total_diamonds_earned += amount

    session.add(WalletLog(
        user_id=user.id, action_type=action_type.value, amount=amount,
        balance_after=wallet.diamonds, meta=meta,
    ))
    await session.flush()
    return wallet.diamonds


async def spend_diamonds(
    session: AsyncSession,
    user: User,
    amount: int,
    action_type: ActionType,
    meta: str | None = None,
) -> bool:
    """برداشت استارز. اگه موجودی کافی نباشه False برمی‌گردونه و چیزی کم نمیشه."""
    if amount <= 0:
        return True

    wallet = await get_or_create_wallet(session, user.id)
    if wallet.diamonds < amount:
        return False

    wallet.diamonds -= amount
    session.add(WalletLog(
        user_id=user.id, action_type=action_type.value, amount=-amount,
        balance_after=wallet.diamonds, meta=meta,
    ))
    await session.flush()
    return True


async def penalize(
    session: AsyncSession,
    user: User,
    amount: int,
    action_type: ActionType,
    meta: str | None = None,
):
    """
    کسر جریمه - برخلاف spend_diamonds، حتی اگه موجودی کافی نباشه هم انجام می‌شه
    (موجودی می‌تونه منفی شه، یعنی کاربر بدهکار می‌شه).
    """
    if amount <= 0:
        return
    wallet = await get_or_create_wallet(session, user.id)
    wallet.diamonds -= amount
    session.add(WalletLog(
        user_id=user.id, action_type=action_type.value, amount=-amount,
        balance_after=wallet.diamonds, meta=meta,
    ))
    await session.flush()

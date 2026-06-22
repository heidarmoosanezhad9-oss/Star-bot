"""سرویس کیف پول: واریز/برداشت الماس با لاگ کامل برای حسابرسی"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Wallet, WalletLog, ActionType
from app.services.vip_trust_service import check_and_upgrade_vip


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
    """واریز الماس به کاربر. amount باید مثبت باشه. برمی‌گردونه موجودی جدید."""
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
    await check_and_upgrade_vip(session, user)
    return wallet.diamonds


async def spend_diamonds(
    session: AsyncSession,
    user: User,
    amount: int,
    action_type: ActionType,
    meta: str | None = None,
) -> bool:
    """برداشت الماس. اگه موجودی کافی نباشه False برمی‌گردونه و چیزی کم نمیشه."""
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

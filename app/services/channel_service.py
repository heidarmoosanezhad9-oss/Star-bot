"""سرویس کانال"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Channel


async def get_or_create_channel(
    session: AsyncSession, chat_id: int, username: str | None, title: str | None,
    owner_user_id: int, description: str | None = None,
) -> Channel:
    result = await session.execute(select(Channel).where(Channel.chat_id == chat_id))
    channel = result.scalar_one_or_none()
    if channel is None:
        channel = Channel(
            chat_id=chat_id, username=username, title=title,
            owner_user_id=owner_user_id, description=description,
        )
        session.add(channel)
        await session.flush()
    else:
        channel.title = title or channel.title
        channel.username = username or channel.username
        if description is not None:
            channel.description = description
    return channel

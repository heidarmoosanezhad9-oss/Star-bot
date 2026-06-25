"""سرویس میشن روزانه و اچیومنت - پیشرفت و پاداش خودکار"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User, Mission, UserMissionProgress, Achievement, UserAchievement, ActionType,
)
from app.services.wallet_service import add_diamonds


async def _get_today_progress(session: AsyncSession, user_id: int, mission: Mission) -> UserMissionProgress:
    result = await session.execute(
        select(UserMissionProgress).where(
            UserMissionProgress.user_id == user_id,
            UserMissionProgress.mission_id == mission.id,
            UserMissionProgress.reset_date == date.today(),
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = UserMissionProgress(user_id=user_id, mission_id=mission.id, reset_date=date.today())
        session.add(progress)
        await session.flush()
    return progress


async def progress_mission(session: AsyncSession, user: User, code: str, increment: int = 1):
    result = await session.execute(select(Mission).where(Mission.code == code, Mission.is_active == True))  # noqa: E712
    mission = result.scalar_one_or_none()
    if mission is None:
        return

    progress = await _get_today_progress(session, user.id, mission)
    if progress.completed:
        return

    progress.progress += increment
    if progress.progress >= mission.target_count:
        progress.completed = True
        await add_diamonds(session, user, mission.reward_diamonds, ActionType.MISSION_REWARD, meta=mission.code)


async def check_achievements(session: AsyncSession, user: User):
    result = await session.execute(select(Achievement).where(Achievement.is_active == True))  # noqa: E712
    achievements = result.scalars().all()

    for ach in achievements:
        already = await session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id, UserAchievement.achievement_id == ach.id
            )
        )
        if already.scalar_one_or_none():
            continue

        current_value = getattr(user, ach.target_field, 0)
        if current_value >= ach.target_value:
            session.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
            if ach.reward_diamonds:
                await add_diamonds(session, user, ach.reward_diamonds, ActionType.ACHIEVEMENT_REWARD, meta=ach.code)

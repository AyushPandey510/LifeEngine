"""
Profile Endpoints
User personalization data used by the Future Self prompt.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis
import structlog

from app.api.v1.auth import get_current_user
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.db import Profile, User
from app.models.schemas import ProfileResponse, ProfileUpdate


router = APIRouter()
logger = structlog.get_logger()


async def _get_or_create_profile(user: User, db: AsyncSession) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile:
        return profile

    profile = Profile(user_id=user.id, display_name=None)
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch the authenticated user's profile."""
    return await _get_or_create_profile(current_user, db)


@router.put("", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Update personalization data and invalidate the profile cache."""
    profile = await _get_or_create_profile(current_user, db)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    try:
        await redis_client.delete(f"user:{current_user.id}:profile")
    except Exception as exc:
        logger.warning("redis_delete_failed", key=f"user:{current_user.id}:profile", error=str(exc))
    return profile

"""
Insights Endpoints
Small retention dashboard derived from user profile and activity.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.db import Decision, Interaction, Profile, User
from app.models.schemas import InsightsResponse


router = APIRouter()


@router.get("", response_model=InsightsResponse)
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a compact MVP insights dashboard."""
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    interaction_count = await db.scalar(
        select(func.count(Interaction.id)).where(Interaction.user_id == current_user.id)
    )
    decision_count = await db.scalar(
        select(func.count(Decision.id)).where(Decision.user_id == current_user.id)
    )

    goals = (profile.goals if profile else []) or []
    habits = (profile.habits if profile else []) or []
    consistency_score = profile.consistency_score if profile else 50

    weekly_insights = []
    if goals:
        weekly_insights.append(f"Your strongest current theme is {goals[0].get('description', 'your first goal')}.")
    else:
        weekly_insights.append("Add one clear goal so your future-self responses can become more specific.")

    if interaction_count:
        weekly_insights.append(f"You have created {interaction_count} memory signals through chat.")
    if decision_count:
        weekly_insights.append(f"You have simulated {decision_count} important decision{'s' if decision_count != 1 else ''}.")

    return InsightsResponse(
        consistency_score=consistency_score,
        consistency_trend=[max(0, min(100, consistency_score + offset)) for offset in [-6, -4, -2, 0, 1, 3, 0]],
        top_goals=goals[:3],
        habit_streaks=habits[:5],
        decision_accuracy=None,
        weekly_insights=weekly_insights,
    )

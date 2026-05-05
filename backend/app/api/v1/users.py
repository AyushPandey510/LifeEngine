"""
User Privacy Endpoints
Data export and account deletion required before launch.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.db import Decision, Interaction, Profile, User, UserDocument
from app.models.schemas import DataExportResponse


router = APIRouter()


@router.get("/me/data-export", response_model=DataExportResponse)
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all personal data as JSON."""
    profile = await db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    interactions = (
        await db.execute(
            select(Interaction)
            .where(Interaction.user_id == current_user.id)
            .order_by(Interaction.created_at)
        )
    ).scalars().all()
    decisions = (
        await db.execute(
            select(Decision)
            .where(Decision.user_id == current_user.id)
            .order_by(Decision.created_at)
        )
    ).scalars().all()
    documents = (
        await db.execute(
            select(UserDocument)
            .where(UserDocument.user_id == current_user.id)
            .order_by(UserDocument.created_at)
        )
    ).scalars().all()

    return DataExportResponse(
        user={
            "id": str(current_user.id),
            "email": current_user.email,
            "plan": current_user.plan,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "consent_given_at": current_user.consent_given_at.isoformat() if current_user.consent_given_at else None,
        },
        profile={
            "display_name": profile.display_name,
            "age": profile.age,
            "goals": profile.goals or [],
            "habits": profile.habits or [],
            "personality": profile.personality or {},
            "consistency_score": profile.consistency_score,
            "risk_tolerance": profile.risk_tolerance,
        } if profile else None,
        interactions=[
            {
                "id": str(item.id),
                "session_id": str(item.session_id),
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in interactions
        ],
        decisions=[
            {
                "id": str(item.id),
                "decision_text": item.decision_text,
                "option_a": item.option_a,
                "option_b": item.option_b,
                "simulation_result": item.simulation_result,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in decisions
        ],
        documents=[
            {
                "id": str(item.id),
                "document_type": item.document_type,
                "filename": item.filename,
                "content_type": item.content_type,
                "extracted_signals": item.extracted_signals or {},
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in documents
        ],
    )


@router.delete("/me")
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete the user immediately; hard purge can run as a scheduled job."""
    current_user.deleted_at = datetime.now(timezone.utc)
    current_user.email = f"deleted-{current_user.id}@lifeengine.local"
    await db.flush()
    return {"status": "deletion_requested"}

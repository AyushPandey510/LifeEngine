from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
import time
import structlog

from app.db.session import get_db
from app.models.db import User
from app.models.db import Conversation
from app.models.db import Interaction
from app.models.schemas import ChatMessageRequest, ChatMessageResponse
from app.api.deps import get_current_user
from app.services.ai_service import generate_ai_response

from app.models.db import UserDocument

logger = structlog.get_logger()
router = APIRouter()


# =========================
# SEND MESSAGE
# =========================

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time = time.time()

    try:
        # ------------------------
        # GET OR CREATE CONVERSATION
        # ------------------------
        conversation = None

        if request.conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == request.conversation_id,
                    Conversation.user_id == current_user.id,
                )
            )
            conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                user_id=current_user.id,
                title=request.message[:50],
            )
            db.add(conversation)
            await db.flush()

        # ------------------------
        # SAVE USER MESSAGE
        # ------------------------
        user_msg = Interaction(
            user_id=current_user.id,
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
        db.add(user_msg)

        # ------------------------
        # GET HISTORY
        # ------------------------
        history = await _get_db_history(db, current_user.id, conversation.id)

        # ------------------------
        # FETCH USER DOCUMENTS (fixed: single .scalars().all() call)
        # ------------------------
        doc_result = await db.execute(
            select(UserDocument).where(UserDocument.user_id == current_user.id)
        )
        user_documents = doc_result.scalars().all()

        # ------------------------
        # CALL AI (documents passed for relevance-based injection)
        # ------------------------
        messages = history + [{"role": "user", "content": request.message}]
        ai_text, tokens = await generate_ai_response(
            messages,
            user_documents=user_documents,
        )

        # ------------------------
        # SAVE AI RESPONSE
        # ------------------------
        latency = int((time.time() - start_time) * 1000)

        ai_msg = Interaction(
            user_id=current_user.id,
            conversation_id=conversation.id,
            role="assistant",
            content=ai_text,
            tokens_used=tokens,
            latency_ms=latency,
        )
        db.add(ai_msg)

        await db.commit()

        return ChatMessageResponse(
            message=ai_text,
            conversation_id=conversation.id,
            tokens_used=tokens,
            latency_ms=latency,
        )

    except Exception as e:
        logger.error("chat_error", error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Chat failed",
        )


# =========================
# GET HISTORY
# =========================

@router.get("/history/{conversation_id}")
async def get_chat_history(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.user_id == current_user.id,
            Interaction.conversation_id == conversation_id,
        )
        .order_by(Interaction.created_at)
    )

    interactions = result.scalars().all()

    return [
        {
            "role": i.role,
            "content": i.content,
            "created_at": i.created_at,
        }
        for i in interactions
    ]


# =========================
# LIST CONVERSATIONS
# =========================

@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            Conversation.updated_at,
            func.count(Interaction.id).label("message_count"),
        )
        .outerjoin(
            Interaction,
            (Interaction.conversation_id == Conversation.id)
            & (Interaction.user_id == current_user.id),
        )
        .where(Conversation.user_id == current_user.id)
        .group_by(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            Conversation.updated_at,
        )
        .order_by(Conversation.updated_at.desc())
    )

    rows = result.all()

    return [
        {
            "id": row.id,
            "title": row.title,
            "message_count": row.message_count,
            "created_at": row.created_at,
        }
        for row in rows
    ]


# =========================
# INTERNAL HISTORY BUILDER
# =========================

async def _get_db_history(db, user_id, conversation_id):
    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.user_id == user_id,
            Interaction.conversation_id == conversation_id,
        )
        .order_by(Interaction.created_at)
        .limit(20)
    )

    interactions = result.scalars().all()

    return [
        {"role": i.role, "content": i.content}
        for i in interactions
    ]
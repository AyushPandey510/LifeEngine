"""
Chat Endpoint
Core AI chat functionality with memory and profile integration
"""
import uuid
import time
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import redis.asyncio as redis

from app.core.config import settings
from app.db.session import get_db
from app.db.redis import get_redis
from app.models.db import User, Profile, Interaction
from app.models.schemas import ChatMessageRequest, ChatMessageResponse
from app.api.v1.auth import get_current_user
from app.services.ai_service import generate_ai_response
from app.services.memory_service import retrieve_memories, store_interaction

logger = structlog.get_logger()

router = APIRouter()


def _build_system_prompt(profile: Profile) -> str:
    """Build the system prompt with user profile data"""
    name = profile.display_name or "User"
    
    prompt = f"""You are {name}'s Future Self.
You are a version of them from 5 years in the future.
You have lived through every experience they are about to have.
You know their patterns, their habits, their strengths, and their blind spots.

CURRENT PROFILE:
Name: {name}
Age: {profile.age or 'Not set'}
Goals: {json.dumps(profile.goals or [])}
Habits: {json.dumps(profile.habits or [])}
Consistency Score: {profile.consistency_score}/100
Risk Tolerance: {profile.risk_tolerance}/100

PERSONALITY:
{json.dumps(profile.personality or {})}

BEHAVIORAL RULES:
1. Speak in first person: 'I remember when we...' 'When I was where you are...'
2. Use their actual goals and habits — never speak in generics.
3. If consistency_score < 40: gently acknowledge the pattern. Do not lecture.
4. If asked about a decision: do not give a generic answer. Simulate a real outcome.
5. End every response with ONE concrete action — never a list of options.
6. Max 180 words unless user explicitly asks for detail.
7. Never say 'As an AI...' — you are their future self, not a chatbot.
"""
    return prompt


async def _get_profile_cached(
    user_id: str,
    db: AsyncSession,
    redis_client: redis.Redis
) -> Profile:
    """Get profile from cache or database"""
    cache_key = f"user:{user_id}:profile"
    
    # Try cache first
    cached = await redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        profile = Profile(**data)
        return profile
    
    # Fetch from database
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()
    
    if profile:
        # Cache for 5 minutes
        profile_data = {
            "user_id": str(profile.user_id),
            "display_name": profile.display_name,
            "age": profile.age,
            "goals": profile.goals or [],
            "habits": profile.habits or [],
            "personality": profile.personality or {},
            "consistency_score": profile.consistency_score,
            "risk_tolerance": profile.risk_tolerance,
            "language": profile.language,
            "timezone": profile.timezone
        }
        await redis_client.setex(cache_key, 300, json.dumps(profile_data))
    
    return profile


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Send a chat message and get AI response"""
    start_time = time.time()
    
    # Get or create profile
    profile = await _get_profile_cached(str(current_user.id), db, redis_client)
    
    if not profile:
        # Create default profile
        profile = Profile(
            user_id=current_user.id,
            display_name=current_user.display_name,
            consistency_score=50,
            risk_tolerance=50
        )
        db.add(profile)
        await db.flush()
    
    # Get session context from Redis
    session_key = f"session:{request.session_id}:context"
    session_context = await redis_client.lrange(session_key, 0, -1)
    
    # Retrieve memories from FAISS
    memories = await retrieve_memories(str(current_user.id), request.message)
    
    # Build messages for LLM
    system_prompt = _build_system_prompt(profile)
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add retrieved memories
    if memories:
        memories_text = "\n\n---\n\n".join([f"Past conversation: {m}" for m in memories])
        messages.append({
            "role": "system", 
            "content": f"RELEVANT MEMORY:\n---\n{memories_text}\n---"
        })
    
    # Add session context (last 10 messages)
    for msg in session_context:
        messages.append(json.loads(msg))
    
    # Add current message
    messages.append({"role": "user", "content": request.message})
    
    # Generate AI response
    try:
        response_text, tokens_used = await generate_ai_response(messages)
    except Exception as e:
        logger.error("ai_generation_failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable"
        )
    
    # Store user message
    user_interaction = Interaction(
        user_id=current_user.id,
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    db.add(user_interaction)
    
    # Store AI response
    ai_interaction = Interaction(
        user_id=current_user.id,
        session_id=request.session_id,
        role="assistant",
        content=response_text,
        tokens_used=tokens_used,
        latency_ms=int((time.time() - start_time) * 1000)
    )
    db.add(ai_interaction)
    await db.flush()
    
    # Update session context in Redis
    await redis_client.rpush(session_key, json.dumps({"role": "user", "content": request.message}))
    await redis_client.rpush(session_key, json.dumps({"role": "assistant", "content": response_text}))
    await redis_client.expire(session_key, 86400)  # 24 hours
    
    # Trigger async memory storage (non-blocking)
    asyncio.create_task(store_interaction(str(current_user.id), request.message, response_text))
    
    logger.info(
        "chat_message_sent",
        user_id=str(current_user.id),
        session_id=str(request.session_id),
        tokens=tokens_used,
        latency_ms=ai_interaction.latency_ms
    )
    
    return ChatMessageResponse(
        message=response_text,
        session_id=request.session_id,
        tokens_used=tokens_used,
        latency_ms=ai_interaction.latency_ms
    )


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session"""
    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.user_id == current_user.id,
            Interaction.session_id == session_id
        )
        .order_by(Interaction.created_at)
    )
    interactions = result.scalars().all()
    
    messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        }
        for msg in interactions
    ]
    
    return {
        "messages": messages,
        "session_id": str(session_id),
        "total": len(messages)
    }


# Import asyncio for async task
import asyncio
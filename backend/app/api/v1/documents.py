"""
Document upload endpoints.

Users can upload resumes, cover letters, certificates, and related files.
The backend parses text, extracts useful personalization signals, stores the
parsed result, and feeds the signal into the Future Self memory/profile.
"""
import asyncio
import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import structlog

from app.api.v1.auth import get_current_user
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.db import Profile, User, UserDocument
from app.models.schemas import DocumentResponse, DocumentUploadResponse
from app.services.document_service import (
    ALLOWED_DOCUMENT_TYPES,
    merge_document_signals,
    parse_uploaded_document,
)
from app.services.memory_service import store_document_chunks, store_interaction


logger = structlog.get_logger()
router = APIRouter()

DocumentType = Literal["resume", "cover_letter", "certificate", "other"]


async def _get_or_create_profile(user: User, db: AsyncSession) -> Profile:
    profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile:
        return profile

    profile = Profile(user_id=user.id, display_name=None)
    db.add(profile)
    await db.flush()
    return profile


async def _safe_redis_delete(redis_client: redis.Redis, key: str) -> None:
    try:
        await redis_client.delete(key)
    except Exception as exc:
        logger.warning("redis_delete_failed", key=key, error=str(exc))


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: DocumentType = Form("other"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Upload and parse a user document for personalization."""
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid document type.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    try:
        content = await file.read()
        parsed = parse_uploaded_document(file.filename, file.content_type, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("document_upload_parse_failed", error=str(exc), filename=file.filename)
        raise HTTPException(status_code=500, detail="Could not parse this document.") from exc

    document = UserDocument(
        user_id=current_user.id,
        document_type=document_type,
        filename=file.filename,
        content_type=file.content_type,
        extracted_text=parsed.text,
        extracted_signals=parsed.signals,
    )
    db.add(document)

    profile = await _get_or_create_profile(current_user, db)
    profile.personality = merge_document_signals(
        profile.personality or {},
        document_type,
        file.filename,
        parsed.signals,
    )

    await db.flush()
    await db.refresh(document)
    await _safe_redis_delete(redis_client, f"user:{current_user.id}:profile")

    memory_message = (
        f"Uploaded {document_type} document '{file.filename}'. "
        f"Extracted signals: {json.dumps(parsed.signals, ensure_ascii=False)[:3000]}"
    )
    asyncio.create_task(store_interaction(str(current_user.id), memory_message, parsed.summary))
    asyncio.create_task(store_document_chunks(str(current_user.id), str(document.id), file.filename, parsed.text))

    logger.info(
        "user_document_uploaded",
        user_id=str(current_user.id),
        document_id=str(document.id),
        document_type=document_type,
        filename=file.filename,
    )

    return DocumentUploadResponse(
        id=document.id,
        document_type=document.document_type,
        filename=document.filename,
        content_type=document.content_type,
        extracted_signals=document.extracted_signals or {},
        created_at=document.created_at,
        summary=parsed.summary,
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List parsed documents for the authenticated user."""
    documents = (
        await db.execute(
            select(UserDocument)
            .where(UserDocument.user_id == current_user.id)
            .order_by(UserDocument.created_at.desc())
        )
    ).scalars().all()
    return documents

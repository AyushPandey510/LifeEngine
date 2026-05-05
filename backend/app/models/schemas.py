"""
Pydantic Schemas
Request and response models for API validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# =========================
# AUTH SCHEMAS
# =========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None
    consent_given: bool


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str]
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# =========================
# PROFILE + MEMORY SCHEMAS
# =========================

class Goal(BaseModel):
    id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: str = "active"   # active | completed | paused
    progress: int = Field(default=0, ge=0, le=100)
    deadline: Optional[datetime] = None


class Habit(BaseModel):
    name: str
    frequency: str  # daily / weekly
    streak: int = 0


class ProfileResponse(BaseModel):
    user_id: UUID
    display_name: Optional[str]
    age: Optional[int]

    # 🧠 MEMORY STRUCTURE
    goals: List[Goal] = Field(default_factory=list)
    habits: List[Habit] = Field(default_factory=list)
    personality: Dict[str, Any] = Field(default_factory=dict)

    consistency_score: int = 50
    risk_tolerance: int = 50

    language: str = "en"
    timezone: str = "Asia/Kolkata"
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    age: Optional[int] = None
    goals: Optional[List[Goal]] = None
    habits: Optional[List[Habit]] = None
    personality: Optional[Dict[str, Any]] = None
    consistency_score: Optional[int] = Field(None, ge=0, le=100)
    risk_tolerance: Optional[int] = Field(None, ge=0, le=100)
    language: Optional[str] = None
    timezone: Optional[str] = None


# =========================
# CHAT (MULTI-PROJECT)
# =========================

class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=160)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=160)


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        from_attributes = True


# =========================
# CHAT MESSAGE
# =========================

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[UUID] = None
    # ❌ REMOVED broken UUID(int=0) logic


class ChatMessageResponse(BaseModel):
    message: str
    conversation_id: UUID

    # 🔥 AI FEATURES
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None

    # 🧠 MEMORY / GOAL ENGINE OUTPUT
    onboarding_updates: Dict[str, Any] = Field(default_factory=dict)
    goal_updates: List[Goal] = Field(default_factory=list)

    # 📊 OPTIONAL INSIGHTS
    suggestions: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: List[Dict[str, Any]]
    conversation_id: UUID
    total: int


# =========================
# DECISION ENGINE
# =========================

class DecisionRequest(BaseModel):
    decision_text: str
    options: List[str]


class OptionResult(BaseModel):
     option: str
     score: int
     reasoning: str


class DecisionResponse(BaseModel):
    id: UUID
    decision_text: str
    options: List[OptionResult]
    recommended: str
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# INSIGHTS
# =========================

class InsightsResponse(BaseModel):
    consistency_score: int
    consistency_trend: List[int] = Field(default_factory=list)
    top_goals: List[Goal] = Field(default_factory=list)
    habit_streaks: List[Habit] = Field(default_factory=list)
    decision_accuracy: Optional[float] = None
    weekly_insights: List[str] = Field(default_factory=list)


# =========================
# DOCUMENT / RESUME
# =========================

class DocumentResponse(BaseModel):
    id: UUID
    document_type: str
    filename: str
    content_type: Optional[str] = None

    # 🧠 PARSED DATA (USED FOR RAG)
    extracted_signals: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(DocumentResponse):
    summary: str


# =========================
# DATA EXPORT (GDPR SAFE)
# =========================

class DataExportResponse(BaseModel):
    user: Dict[str, Any]
    profile: Optional[Dict[str, Any]] = None
    interactions: List[Dict[str, Any]] = Field(default_factory=list)
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)


# =========================
# ERROR
# =========================

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
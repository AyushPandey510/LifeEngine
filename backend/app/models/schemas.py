"""
Pydantic Schemas
Request and response models for API validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# Auth Schemas
class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: str
    display_name: Optional[str]
    plan: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data"""
    user_id: Optional[str] = None


# Profile Schemas
class ProfileResponse(BaseModel):
    """Schema for profile response"""
    user_id: UUID
    display_name: Optional[str]
    age: Optional[int]
    goals: List[Dict[str, Any]] = []
    habits: List[Dict[str, Any]] = []
    personality: Dict[str, Any] = {}
    consistency_score: int = 50
    risk_tolerance: int = 50
    language: str = "en"
    timezone: str = "Asia/Kolkata"
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    """Schema for profile update"""
    display_name: Optional[str] = None
    age: Optional[int] = None
    goals: Optional[List[Dict[str, Any]]] = None
    habits: Optional[List[Dict[str, Any]]] = None
    personality: Optional[Dict[str, Any]] = None
    consistency_score: Optional[int] = Field(None, ge=0, le=100)
    risk_tolerance: Optional[int] = Field(None, ge=0, le=100)
    language: Optional[str] = None
    timezone: Optional[str] = None


# Chat Schemas
class ChatMessageRequest(BaseModel):
    """Schema for chat message request"""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: UUID


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    message: str
    session_id: UUID
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    
    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response"""
    messages: List[Dict[str, Any]]
    session_id: UUID
    total: int


# Decision Schemas
class DecisionRequest(BaseModel):
    """Schema for decision simulation request"""
    decision_text: str = Field(..., min_length=1, max_length=5000)
    option_a: str = Field(..., min_length=1, max_length=2000)
    option_b: str = Field(..., min_length=1, max_length=2000)


class OptionResult(BaseModel):
    """Schema for decision option result"""
    option: str
    probability_score: int
    narrative: str


class DecisionResponse(BaseModel):
    """Schema for decision simulation response"""
    id: UUID
    decision_text: str
    option_a_result: OptionResult
    option_b_result: OptionResult
    recommendation: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Insights Schemas
class InsightsResponse(BaseModel):
    """Schema for insights dashboard response"""
    consistency_score: int
    consistency_trend: List[int]  # Last 30 days
    top_goals: List[Dict[str, Any]]
    habit_streaks: List[Dict[str, Any]]
    decision_accuracy: Optional[float] = None
    weekly_insights: List[str]


# Error Schemas
class ErrorResponse(BaseModel):
    """Schema for error response"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
"""
Database Models
SQLAlchemy ORM models for Life Engine AI
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    """User model - the identity layer"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    plan = Column(String(20), default="free")  # free, premium, enterprise
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    last_active = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Profile(Base):
    """Profile model - the personalization layer"""
    __tablename__ = "profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    goals = Column(JSON, default=list)  # [{category, description, timeline}]
    habits = Column(JSON, default=list)  # [{name, frequency, streak, last_done}]
    personality = Column(JSON, default=dict)  # Big Five scores
    consistency_score = Column(Integer, default=50)  # 0-100
    risk_tolerance = Column(Integer, default=50)  # 0-100
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="Asia/Kolkata")
    updated_at = Column(DateTime(timezone=True), onupdate=text("now()"))
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<Profile(user_id={self.user_id}, name={self.display_name})>"


class Interaction(Base):
    """Interaction model - stores every conversation"""
    __tablename__ = "interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user or assistant
    content = Column(Text, nullable=False)
    embedding_id = Column(String(100), nullable=True)  # FAISS index ID
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    
    def __repr__(self):
        return f"<Interaction(id={self.id}, user_id={self.user_id}, role={self.role})>"


class Decision(Base):
    """Decision model - stores user decisions for simulation"""
    __tablename__ = "decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    simulation_result = Column(JSON, nullable=True)
    actual_outcome = Column(String(50), nullable=True)  # better, worse, expected
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    outcome_reported_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="decisions")
    
    def __repr__(self):
        return f"<Decision(id={self.id}, user_id={self.user_id})>"
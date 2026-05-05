"""
Database Models
SQLAlchemy ORM models for Life Engine AI
"""

import uuid
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


# =========================
# USER
# =========================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    plan = Column(String(20), default="free")
    is_verified = Column(Boolean, default=False)
    consent_given_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    last_active = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


# =========================
# PROFILE (MEMORY + GOALS)
# =========================

class Profile(Base):
    __tablename__ = "profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    display_name = Column(String(100))
    age = Column(Integer)

    # 🧠 CORE MEMORY STRUCTURE
    goals = Column(JSON, default=list)
    habits = Column(JSON, default=list)
    personality = Column(JSON, default=dict)

    consistency_score = Column(Integer, default=50)
    risk_tolerance = Column(Integer, default=50)

    language = Column(String(10), default="en")
    timezone = Column(String(50), default="Asia/Kolkata")

    updated_at = Column(DateTime(timezone=True), onupdate=text("now()"))

    user = relationship("User", back_populates="profile")


# =========================
# CONVERSATION (PROJECTS)
# =========================

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(160), nullable=False, default="New project")

    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), index=True)

    user = relationship("User", back_populates="conversations")

    # ✅ IMPORTANT (you were missing this)
    interactions = relationship(
        "Interaction",
        primaryjoin="Conversation.id==foreign(Interaction.conversation_id)",
        cascade="all, delete-orphan"
    )


# =========================
# INTERACTION (CHAT + MEMORY)
# =========================

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ✅ FIXED (aligned everywhere)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)

    # 🧠 MEMORY SUPPORT
    embedding_id = Column(String(100), nullable=True)
    memory_type = Column(String(50), default="short_term")  
    # short_term | long_term | goal | document

    tokens_used = Column(Integer)
    latency_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)

    user = relationship("User", back_populates="interactions")

    # ✅ IMPORTANT RELATIONSHIP
    conversation = relationship(
        "Conversation",
        primaryjoin="foreign(Interaction.conversation_id)==Conversation.id"
    )


# =========================
# DECISION ENGINE
# =========================

class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    decision_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)

    simulation_result = Column(JSON)
    actual_outcome = Column(String(50))

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    outcome_reported_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="decisions")


# =========================
# DOCUMENTS (RESUME / RAG)
# =========================

class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    document_type = Column(String(40), nullable=False)
    filename = Column(String(255), nullable=False)

    content_type = Column(String(120))
    extracted_text = Column(Text, nullable=False)

    # 🧠 USED FOR AI CONTEXT
    extracted_signals = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)

    user = relationship("User", back_populates="documents")
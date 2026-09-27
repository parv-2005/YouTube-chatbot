"""
Database ORM Models
===================
SQLAlchemy ORM models that map Python classes to PostgreSQL tables.

Relationships:
  users ──< conversations ──< messages
                 │
  videos ────────┘

  One user    → many conversations
  One video   → many conversations
  One conversation → many messages
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Text, DateTime,
    ForeignKey, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.session import Base


def utcnow():
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    Registered user.
    Passwords are stored as bcrypt hashes — never plaintext.
    """
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # One user → many conversations
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Video(Base):
    """
    Represents an ingested YouTube video.

    transcript_source: 'youtube' or 'whisper'
        Tracks whether the transcript came from YouTube's API
        or our local Whisper fallback.

    status: 'pending' → 'processing' → 'ready' or 'failed'
        Tracks the ingestion pipeline progress.
    """
    __tablename__ = "videos"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    youtube_video_id = Column(
        String(20), unique=True, nullable=False, index=True
    )
    url = Column(Text, nullable=False)
    title = Column(String(500))
    channel_name = Column(String(255))
    duration_seconds = Column(Integer)
    transcript_source = Column(
        String(20), nullable=False, default="youtube"
    )
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    processed_at = Column(DateTime(timezone=True))

    # One video → many conversations
    conversations = relationship(
        "Conversation",
        back_populates="video",
        cascade="all, delete-orphan"
    )


class Conversation(Base):
    """
    A chat session between a user and a video.
    Users can have multiple conversations about the same video.
    """
    __tablename__ = "conversations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    title = Column(String(500), default="New Conversation")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="conversations")
    video = relationship("Video", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_video_id", "video_id"),
    )


class Message(Base):
    """
    A single message in a conversation.
    role: 'user' or 'assistant'
    sources: JSON array of source chunks with timestamps
    """
    __tablename__ = "messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(JSON)  # [{"text": "...", "start_time": 72.5, ...}]
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "created_at"),
    )

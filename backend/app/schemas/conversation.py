"""
Conversation Schemas
====================
Request/response models for conversation management.
"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class ConversationCreate(BaseModel):
    """Request body for POST /api/conversations"""
    video_id: UUID
    title: Optional[str] = "New Conversation"


class MessageResponse(BaseModel):
    """A single message in a conversation."""
    id: UUID
    role: str
    content: str
    sources: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response for a conversation with its messages."""
    id: UUID
    video_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    video_title: Optional[str] = None
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Summary of a conversation for list views."""
    id: UUID
    video_id: UUID
    title: str
    video_title: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response for GET /api/conversations"""
    conversations: list[ConversationListItem]
    total: int

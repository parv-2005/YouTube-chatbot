"""
Chat Schemas
============
Request/response models for the chat endpoints.
Includes source references with YouTube timestamp links.
"""

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class SourceReference(BaseModel):
    """
    A source chunk from the video transcript.
    Includes the text and the YouTube timestamp link
    so users can jump to that point in the video.
    """
    text: str
    video_id: str
    start_time: float
    end_time: float
    timestamp_label: str           # "01:12"
    timestamp_link: str            # "https://youtube.com/watch?v=xyz&t=72"


class ChatRequest(BaseModel):
    """Request body for POST /api/chat and /api/chat/stream"""
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Response for POST /api/chat"""
    answer: str
    sources: list[SourceReference]


class StreamToken(BaseModel):
    """A single token in a streaming response."""
    token: str = ""
    done: bool = False
    sources: list[SourceReference] = []

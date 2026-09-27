"""
Video Schemas
=============
Request/response models for video ingestion endpoints.
"""

from pydantic import BaseModel, Field, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional


class VideoIngestRequest(BaseModel):
    """Request body for POST /api/videos/ingest"""
    url: str = Field(
        description="YouTube video URL",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    )


class VideoResponse(BaseModel):
    """Response representing a processed video."""
    id: UUID
    youtube_video_id: str
    url: str
    title: Optional[str] = None
    channel_name: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript_source: str
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """Response for GET /api/videos"""
    videos: list[VideoResponse]
    total: int

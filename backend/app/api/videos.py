"""
Videos API
==========
Endpoints for ingesting and listing YouTube videos.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.database.models import User, Video
from app.schemas.video import VideoIngestRequest, VideoResponse, VideoListResponse
from app.services.ingestion_service import ingest_video
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=VideoResponse)
def ingest(
    data: VideoIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ingest a YouTube video.

    Runs the full pipeline:
    URL → Transcript (YouTube/Whisper) → Clean → Chunk → Embed → Store

    Returns the video record with processing status.
    """
    try:
        video = ingest_video(data.url, db)
        return video

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("", response_model=VideoListResponse)
def list_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all ingested videos."""
    videos = (
        db.query(Video)
        .order_by(Video.created_at.desc())
        .all()
    )

    return VideoListResponse(
        videos=videos,
        total=len(videos),
    )


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific video."""
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    return video

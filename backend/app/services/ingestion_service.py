"""
Ingestion Service
=================
Orchestrates the complete video ingestion pipeline:

YouTube URL → Validate → Transcript → Clean → Chunk → Embed → Store

This is the "glue" that connects all the individual services
into a single, cohesive pipeline.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.models import Video
from app.utils.youtube_utils import extract_video_id, is_valid_youtube_url
from app.services.transcript_service import get_transcript
from app.services.cleaning_service import clean_segments
from app.services.chunking_service import create_chunks
from app.services.vector_store import store_chunks
from app.services.bm25_service import build_bm25_index
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def ingest_video(url: str, db: Session) -> Video:
    """
    Complete video ingestion pipeline.

    Steps:
    1. Validate the YouTube URL
    2. Check if the video is already ingested
    3. Extract the transcript (YouTube → Whisper fallback)
    4. Clean the transcript text
    5. Chunk the transcript with timestamps
    6. Generate embeddings and store in Qdrant
    7. Build the BM25 keyword index
    8. Save video metadata to PostgreSQL

    Args:
        url: YouTube video URL
        db: Database session

    Returns:
        The Video database record.

    Raises:
        ValueError: If the URL is invalid
        RuntimeError: If ingestion fails
    """
    # ── Step 1: Validate URL ─────────────────────────────
    if not is_valid_youtube_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    video_id = extract_video_id(url)

    logger.info("ingestion_started", video_id=video_id, url=url)

    # ── Step 2: Check if already ingested ────────────────
    existing = db.query(Video).filter(
        Video.youtube_video_id == video_id
    ).first()

    if existing and existing.status == "ready":
        logger.info("video_already_ingested", video_id=video_id)
        return existing

    # Create or update the video record
    if existing:
        video = existing
    else:
        video = Video(
            youtube_video_id=video_id,
            url=url,
            status="processing",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

    try:
        video.status = "processing"
        db.commit()

        # ── Step 3: Extract transcript ───────────────────
        # This tries YouTube first, falls back to Whisper
        segments, transcript_source = get_transcript(video_id)

        video.transcript_source = transcript_source

        logger.info(
            "transcript_extracted",
            video_id=video_id,
            source=transcript_source,
            segment_count=len(segments),
        )

        # ── Step 4: Clean transcript ─────────────────────
        cleaned = clean_segments(segments)

        logger.info(
            "transcript_cleaned",
            video_id=video_id,
            before=len(segments),
            after=len(cleaned),
        )

        # ── Step 5: Chunk with timestamps ────────────────
        chunks = create_chunks(cleaned, video_id)

        logger.info(
            "chunks_created",
            video_id=video_id,
            chunk_count=len(chunks),
        )

        # ── Step 6: Embed and store in Qdrant ────────────
        stored_count = store_chunks(chunks)

        # ── Step 7: Build BM25 index ─────────────────────
        build_bm25_index(video_id, chunks)

        # ── Step 8: Update database record ───────────────
        video.chunk_count = stored_count
        video.status = "ready"
        video.processed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "ingestion_complete",
            video_id=video_id,
            transcript_source=transcript_source,
            chunk_count=stored_count,
        )

        return video

    except Exception as e:
        # Mark the video as failed and store the error
        video.status = "failed"
        video.error_message = str(e)
        db.commit()

        logger.error(
            "ingestion_failed",
            video_id=video_id,
            error=str(e),
        )

        raise RuntimeError(f"Video ingestion failed: {str(e)}")

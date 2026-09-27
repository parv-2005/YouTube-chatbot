"""
Transcript Service
==================
Orchestrates transcript extraction with automatic fallback.

This is the KEY module that ensures the system NEVER fails
just because YouTube doesn't provide a transcript.

Flow:
    1. Try YouTube Transcript API (fast, free)
    2. If unavailable → Download audio via yt-dlp
    3. Run local Whisper on the audio
    4. Clean up temporary audio file
    5. Return transcript in common format

The rest of the system (chunking, embedding, retrieval)
does NOT know or care which source the transcript came from.
"""

from typing import Tuple

from app.services.youtube_service import get_youtube_transcript
from app.services.audio_service import download_audio, cleanup_audio
from app.services.whisper_service import transcribe_audio
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_transcript(video_id: str) -> Tuple[list[dict], str]:
    """
    Get a transcript for a YouTube video, with automatic Whisper fallback.

    Args:
        video_id: YouTube video ID (11 characters)

    Returns:
        Tuple of (segments, source) where:
        - segments: List of dicts with {text, start_time, end_time}
        - source: "youtube" or "whisper"

    Raises:
        RuntimeError: If BOTH YouTube and Whisper fail.
    """

    # ── Step 1: Try YouTube transcript ────────────────────
    # This is the fast path — no audio download needed.
    segments = get_youtube_transcript(video_id)

    if segments and len(segments) > 0:
        logger.info(
            "transcript_source_selected",
            video_id=video_id,
            source="youtube",
            segment_count=len(segments)
        )
        return segments, "youtube"

    # ── Step 2: Fallback to Whisper ───────────────────────
    # YouTube doesn't have a transcript for this video.
    # We'll download the audio and transcribe it locally.
    logger.info(
        "falling_back_to_whisper",
        video_id=video_id
    )

    audio_path = None

    try:
        # Download audio from YouTube
        audio_path = download_audio(video_id)

        # Transcribe using local Whisper
        segments = transcribe_audio(audio_path)

        if not segments:
            raise RuntimeError("Whisper produced empty transcript")

        logger.info(
            "transcript_source_selected",
            video_id=video_id,
            source="whisper",
            segment_count=len(segments)
        )

        return segments, "whisper"

    except Exception as e:
        logger.error(
            "transcript_extraction_failed",
            video_id=video_id,
            error=str(e)
        )
        raise RuntimeError(
            f"Could not extract transcript from video: {str(e)}. "
            f"Tried YouTube transcript API and local Whisper."
        )

    finally:
        # Always clean up the temporary audio file
        if audio_path:
            cleanup_audio(audio_path)

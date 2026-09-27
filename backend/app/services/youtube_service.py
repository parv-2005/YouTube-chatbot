"""
YouTube Service
===============
Handles YouTube URL parsing and transcript extraction using
the youtube-transcript-api library.

This is the FIRST source of transcripts. If this fails
(no transcript available), the system falls back to Whisper.
"""

from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi

from app.core.logging_config import get_logger
from app.utils.youtube_utils import extract_video_id

logger = get_logger(__name__)


# ── Common Transcript Format ────────────────────────────────
# Every transcript segment — whether from YouTube or Whisper —
# is normalized to this structure before downstream processing.
#
# {
#     "text": "The spoken text content",
#     "start_time": 70.5,   (seconds from video start)
#     "end_time": 75.7      (seconds from video start)
# }
#
# This ensures the chunking, embedding, and retrieval pipeline
# works identically regardless of the transcript source.


def get_youtube_transcript(video_id: str) -> Optional[list[dict]]:
    """
    Attempt to fetch a transcript from YouTube's API.

    YouTube provides transcripts for videos with:
    - Manual subtitles uploaded by the creator
    - Auto-generated captions

    Strategy:
    1. Try English transcript directly
    2. Try Hindi and other common languages
    3. Try fetching any available language and translating to English

    Returns:
        List of transcript segments in common format,
        or None if no transcript is available.
    """
    api = YouTubeTranscriptApi()

    logger.info(
        "fetching_youtube_transcript",
        video_id=video_id
    )

    # ── Strategy 1: Try English directly ─────────────────
    try:
        transcript = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        return _normalize_transcript(transcript, video_id, "en")
    except Exception:
        pass

    # ── Strategy 2: Try common languages directly ────────
    common_languages = ["hi", "es", "fr", "de", "pt", "ja", "ko", "zh-Hans", "ar", "ru"]
    try:
        transcript = api.fetch(video_id, languages=common_languages)
        return _normalize_transcript(transcript, video_id, "native")
    except Exception:
        pass

    # ── Strategy 3: List available and try any ───────────
    try:
        transcript_list = api.list(video_id)

        # Try to find any transcript and fetch it
        for t in transcript_list:
            try:
                transcript = api.fetch(video_id, languages=[t.language_code])
                return _normalize_transcript(transcript, video_id, t.language_code)
            except Exception:
                continue

    except Exception as e:
        logger.info(
            "youtube_transcript_unavailable",
            video_id=video_id,
            reason=str(e)
        )

    return None


def _normalize_transcript(transcript, video_id: str, lang: str) -> list[dict]:
    """Normalize YouTube transcript to our common segment format."""
    segments = []
    for item in transcript:
        segments.append({
            "text": item.text,
            "start_time": item.start,
            "end_time": item.start + item.duration,
        })

    logger.info(
        "youtube_transcript_success",
        video_id=video_id,
        language=lang,
        segment_count=len(segments)
    )

    return segments

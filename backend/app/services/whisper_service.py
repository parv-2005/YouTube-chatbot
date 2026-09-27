"""
Whisper Service
===============
Local speech-to-text transcription using OpenAI's Whisper model.

This is the FALLBACK when YouTube doesn't provide a transcript.

Why Whisper?
- Completely free and open-source
- Runs locally — no API calls, no costs
- Produces high-quality timestamped transcripts
- Supports 100+ languages

Model sizes and tradeoffs:
  tiny  → ~1 GB RAM, fastest,  lowest quality
  base  → ~1 GB RAM, fast,     good quality     ← DEFAULT
  small → ~2 GB RAM, moderate, better quality
  medium→ ~5 GB RAM, slow,     great quality
  large → ~10 GB RAM, slowest, best quality

On a CPU (no GPU), the 'base' model transcribes roughly
10x real-time (a 10-minute video takes ~1 minute).
"""

import whisper

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# The Whisper model is loaded once and reused for all transcriptions.
# This avoids re-loading the model (which is slow) on every request.
_whisper_model = None


def _get_whisper_model():
    """
    Lazy-load the Whisper model.
    The model is downloaded on first use and cached locally by Whisper.
    """
    global _whisper_model

    if _whisper_model is None:
        model_size = settings.WHISPER_MODEL_SIZE

        logger.info(
            "loading_whisper_model",
            model_size=model_size
        )

        _whisper_model = whisper.load_model(model_size)

        logger.info("whisper_model_loaded", model_size=model_size)

    return _whisper_model


def transcribe_audio(audio_path: str) -> list[dict]:
    """
    Transcribe an audio file using local Whisper.

    The output is normalized to our common transcript format:
    [
        {
            "text": "The spoken words",
            "start_time": 10.5,
            "end_time": 15.2
        },
        ...
    ]

    Args:
        audio_path: Path to the audio file (WAV preferred)

    Returns:
        List of transcript segments in common format.

    Raises:
        RuntimeError: If transcription fails.
    """
    try:
        model = _get_whisper_model()

        logger.info(
            "whisper_transcription_started",
            audio_path=audio_path
        )

        # Whisper returns a dict with:
        # - "text": full transcript
        # - "segments": list of timestamped segments
        # - "language": detected language
        result = model.transcribe(
            audio_path,
            # word_timestamps=False keeps it at segment level,
            # which is more practical for chunking
            word_timestamps=False,
            verbose=False,
        )

        # Normalize Whisper's output to our common format
        segments = []
        for segment in result["segments"]:
            text = segment["text"].strip()

            # Skip empty segments
            if not text:
                continue

            segments.append({
                "text": text,
                "start_time": segment["start"],
                "end_time": segment["end"],
            })

        logger.info(
            "whisper_transcription_complete",
            segment_count=len(segments),
            language=result.get("language", "unknown")
        )

        return segments

    except Exception as e:
        logger.error(
            "whisper_transcription_failed",
            audio_path=audio_path,
            error=str(e)
        )
        raise RuntimeError(f"Whisper transcription failed: {str(e)}")

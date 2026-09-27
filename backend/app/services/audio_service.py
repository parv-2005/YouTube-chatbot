"""
Audio Service
=============
Downloads audio from YouTube videos using yt-dlp.

This is used ONLY when YouTube doesn't provide a transcript.
The downloaded audio is then sent to Whisper for transcription.

yt-dlp is the most actively maintained YouTube downloader.
It handles:
- Age-restricted videos
- Various audio formats
- Rate limiting and retries
"""

import os
import tempfile

import yt_dlp

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def download_audio(video_id: str) -> str:
    """
    Download audio from a YouTube video as a WAV file.

    Whisper works best with WAV format at 16kHz.
    We use yt-dlp to download and ffmpeg to convert.

    Args:
        video_id: YouTube video ID

    Returns:
        Path to the downloaded audio file.

    Raises:
        RuntimeError: If download or conversion fails.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Create a temporary file for the audio.
    # We use a temp directory so files are cleaned up by the OS.
    output_dir = tempfile.mkdtemp(prefix="yt_audio_")
    output_path = os.path.join(output_dir, f"{video_id}.wav")

    logger.info(
        "downloading_audio",
        video_id=video_id,
        output_path=output_path
    )

    # yt-dlp configuration:
    # - Extract only audio (no video)
    # - Convert to WAV format (Whisper's preferred format)
    # - Use best audio quality available
    # - 'bestaudio*' is more permissive than 'bestaudio/best'
    #   and works with more video types
    ydl_opts = {
        "format": "bestaudio*/best",
        "outtmpl": os.path.join(output_dir, f"{video_id}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
        # Improve compatibility with geo-restricted/age-restricted content
        "geo_bypass": True,
        "nocheckcertificate": True,
        # Retry on failures
        "retries": 3,
        "fragment_retries": 3,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(output_path):
            # Sometimes the output extension differs; find any audio file
            for f in os.listdir(output_dir):
                if f.startswith(video_id) and f.endswith(".wav"):
                    output_path = os.path.join(output_dir, f)
                    break

        if not os.path.exists(output_path):
            raise RuntimeError(
                f"Audio file not found after download: {output_path}"
            )

        logger.info(
            "audio_download_success",
            video_id=video_id,
            file_size_mb=round(
                os.path.getsize(output_path) / (1024 * 1024), 2
            )
        )

        return output_path

    except Exception as e:
        # Retry with a completely permissive format string
        logger.warning(
            "audio_download_retrying",
            video_id=video_id,
            error=str(e)
        )

        try:
            ydl_opts["format"] = "worst"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if not os.path.exists(output_path):
                for f in os.listdir(output_dir):
                    if f.startswith(video_id) and f.endswith(".wav"):
                        output_path = os.path.join(output_dir, f)
                        break

            if os.path.exists(output_path):
                logger.info(
                    "audio_download_success_retry",
                    video_id=video_id,
                )
                return output_path

        except Exception:
            pass

        logger.error(
            "audio_download_failed",
            video_id=video_id,
            error=str(e)
        )
        raise RuntimeError(f"Failed to download audio: {str(e)}")


def cleanup_audio(audio_path: str):
    """
    Remove the temporary audio file and its directory.
    Called after Whisper has finished transcribing.
    """
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # Also remove the parent temp directory
        parent_dir = os.path.dirname(audio_path)
        if os.path.exists(parent_dir) and parent_dir.startswith(
            tempfile.gettempdir()
        ):
            os.rmdir(parent_dir)

    except OSError as e:
        # Non-critical — temp files will be cleaned up eventually
        logger.warning("cleanup_failed", path=audio_path, error=str(e))

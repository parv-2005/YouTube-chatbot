"""
YouTube URL Utilities
=====================
Functions for validating YouTube URLs and extracting video IDs.

YouTube URLs come in many formats:
  - https://www.youtube.com/watch?v=VIDEO_ID
  - https://youtube.com/watch?v=VIDEO_ID&t=120
  - https://youtu.be/VIDEO_ID
  - https://youtu.be/VIDEO_ID?t=120
  - https://www.youtube.com/embed/VIDEO_ID
  - https://m.youtube.com/watch?v=VIDEO_ID

A video ID is always 11 characters: letters, numbers, hyphens, underscores.
"""

import re
from typing import Optional


# Regex pattern to extract YouTube video IDs from various URL formats.
# Matches: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID
YOUTUBE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?(?:"
    r"youtube\.com/(?:watch\?v=|embed/|v/)"  # youtube.com formats
    r"|youtu\.be/"                            # short URL format
    r")([\w-]{11})"                           # capture the 11-char video ID
)


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract the 11-character video ID from any YouTube URL format.

    Returns None if the URL is not a valid YouTube URL.

    Examples:
        extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        → "dQw4w9WgXcQ"

        extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        → "dQw4w9WgXcQ"

        extract_video_id("not a youtube url")
        → None
    """
    match = YOUTUBE_URL_PATTERN.search(url)

    if match:
        return match.group(1)

    return None


def is_valid_youtube_url(url: str) -> bool:
    """Check if a string is a valid YouTube URL."""
    return extract_video_id(url) is not None


def build_youtube_url(video_id: str) -> str:
    """Build a standard YouTube URL from a video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"

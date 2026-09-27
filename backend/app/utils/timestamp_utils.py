"""
Timestamp Utilities
===================
Convert between seconds and human-readable timestamps.
Build clickable YouTube timestamp links.
"""


def seconds_to_timestamp(seconds: float) -> str:
    """
    Convert seconds to a human-readable timestamp.

    Examples:
        seconds_to_timestamp(72.5)   → "01:12"
        seconds_to_timestamp(3661.0) → "1:01:01"
        seconds_to_timestamp(5.0)    → "00:05"
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def build_timestamp_link(video_id: str, start_seconds: float) -> str:
    """
    Build a YouTube URL that jumps to a specific timestamp.

    YouTube's &t= parameter accepts whole seconds.

    Example:
        build_timestamp_link("abc123", 72.5)
        → "https://www.youtube.com/watch?v=abc123&t=72"
    """
    t = int(start_seconds)
    return f"https://www.youtube.com/watch?v={video_id}&t={t}"

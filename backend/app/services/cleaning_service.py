"""
Cleaning Service
================
Cleans raw transcript text before chunking.

YouTube auto-generated transcripts often contain:
- [Music], [Applause], [Laughter] markers
- Excessive whitespace and newlines
- Filler words (common in auto-captions)

Whisper transcripts are generally cleaner but may have:
- Repeated words (hallucination artifacts)
- Minor formatting issues

This service normalizes text so the RAG pipeline
gets clean, consistent input.
"""

import re
from typing import List


# Patterns to remove from transcript text.
# These are common markers inserted by YouTube's auto-captioning system.
YOUTUBE_MARKERS = re.compile(
    r"\[(?:Music|Applause|Laughter|Cheering|Silence)\]",
    re.IGNORECASE
)

# Multiple spaces, newlines, tabs → single space
WHITESPACE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Clean a single piece of transcript text.

    Removes:
    - YouTube auto-caption markers ([Music], etc.)
    - Excessive whitespace
    - Leading/trailing whitespace
    """
    # Remove YouTube markers
    text = YOUTUBE_MARKERS.sub("", text)

    # Normalize whitespace
    text = WHITESPACE.sub(" ", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def clean_segments(segments: list[dict]) -> list[dict]:
    """
    Clean all transcript segments.

    Removes segments that are empty after cleaning
    (e.g., segments that were only "[Music]").

    Args:
        segments: List of {text, start_time, end_time} dicts

    Returns:
        Cleaned list with empty segments removed.
    """
    cleaned = []

    for segment in segments:
        cleaned_text = clean_text(segment["text"])

        # Skip segments that are empty after cleaning
        if not cleaned_text:
            continue

        cleaned.append({
            "text": cleaned_text,
            "start_time": segment["start_time"],
            "end_time": segment["end_time"],
        })

    return cleaned

"""
Chunking Service
================
Splits cleaned transcript text into chunks suitable for embedding.

Why chunking matters:
- Embedding models have token limits
- Smaller chunks = more precise retrieval
- Overlapping chunks prevent information loss at boundaries

Our approach:
1. Accumulate transcript segments until we reach ~500 characters
2. Use LangChain's RecursiveCharacterTextSplitter to split cleanly
3. Preserve the start_time and end_time from the original segments
4. Each chunk carries its video_id for source attribution

This produces chunks like:
{
    "text": "Neural networks consist of layers...",
    "video_id": "abc123",
    "start_time": 72.5,
    "end_time": 85.0
}
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def create_chunks(
    segments: list[dict],
    video_id: str,
) -> list[dict]:
    """
    Convert transcript segments into overlapping text chunks.

    The algorithm:
    1. Concatenate segments until the accumulated text exceeds CHUNK_SIZE
    2. Split the accumulated text using RecursiveCharacterTextSplitter
    3. Track start/end timestamps from the contributing segments
    4. Repeat until all segments are processed

    Args:
        segments: Cleaned transcript segments [{text, start_time, end_time}]
        video_id: YouTube video ID for source attribution

    Returns:
        List of chunk dicts [{text, video_id, start_time, end_time}]
    """
    # RecursiveCharacterTextSplitter tries to split at natural boundaries:
    # paragraphs → sentences → words → characters
    # This produces more coherent chunks than splitting mid-word.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )

    chunks = []
    current_text = ""
    chunk_start_time = None
    chunk_end_time = None

    for segment in segments:
        text = segment["text"]

        # Track the start time of the first segment in this chunk
        if chunk_start_time is None:
            chunk_start_time = segment["start_time"]

        current_text += " " + text
        chunk_end_time = segment["end_time"]

        # When accumulated text is large enough, split it
        if len(current_text) >= settings.CHUNK_SIZE:
            split_texts = splitter.split_text(current_text.strip())

            for split_text in split_texts:
                chunks.append({
                    "text": split_text,
                    "video_id": video_id,
                    "start_time": chunk_start_time,
                    "end_time": chunk_end_time,
                })

            # Reset for next chunk group
            current_text = ""
            chunk_start_time = None

    # Don't forget any remaining text that didn't reach CHUNK_SIZE
    if current_text.strip():
        chunks.append({
            "text": current_text.strip(),
            "video_id": video_id,
            "start_time": chunk_start_time,
            "end_time": chunk_end_time,
        })

    logger.info(
        "chunking_complete",
        video_id=video_id,
        input_segments=len(segments),
        output_chunks=len(chunks),
        chunk_size=settings.CHUNK_SIZE,
    )

    return chunks

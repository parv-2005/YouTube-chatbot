"""
BM25 Service
============
Keyword-based search using the BM25 (Okapi) algorithm.

Why BM25 in addition to vector search?
- Vector search finds SEMANTICALLY similar text
  (catches paraphrases, synonyms, related concepts)
- BM25 finds EXACT KEYWORD matches
  (catches specific terms, names, acronyms)

Example where BM25 helps:
  Query: "What is LSTM?"
  Vector search might find chunks about "recurrent networks"
  (semantically related but might miss the exact term "LSTM")
  BM25 will find chunks containing "LSTM" directly.

BM25 scoring considers:
- Term frequency (TF): how often a word appears in the document
- Inverse document frequency (IDF): rare words score higher
- Document length normalization: longer documents don't get unfair advantage
"""

from typing import Optional

from rank_bm25 import BM25Okapi

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ── In-Memory BM25 Index ────────────────────────────────────
# BM25 indexes are stored in memory per video.
# In production, you might use Elasticsearch for persistent keyword search.
# For this project, we rebuild from Qdrant payloads on startup if needed.

_bm25_indexes: dict[str, BM25Okapi] = {}
_bm25_chunks: dict[str, list[dict]] = {}


def build_bm25_index(video_id: str, chunks: list[dict]):
    """
    Build a BM25 index for a specific video's chunks.

    Tokenization is simple (lowercase + split on whitespace).
    For production, you might use a proper tokenizer with
    stemming and stopword removal.

    Args:
        video_id: YouTube video ID
        chunks: List of chunk dicts [{text, video_id, start_time, end_time}]
    """
    # Tokenize each chunk's text
    tokenized_docs = [
        chunk["text"].lower().split()
        for chunk in chunks
    ]

    # Build the BM25 index
    _bm25_indexes[video_id] = BM25Okapi(tokenized_docs)
    _bm25_chunks[video_id] = chunks

    logger.info(
        "bm25_index_built",
        video_id=video_id,
        document_count=len(chunks)
    )


def bm25_search(
    query: str,
    top_k: int = 20,
    video_id: Optional[str] = None
) -> list[dict]:
    """
    Keyword search using BM25.

    Args:
        query: User's search query
        top_k: Number of results to return
        video_id: Optional filter for a specific video

    Returns:
        List of result dicts with text, metadata, and BM25 score.
    """
    results = []

    # Determine which video indexes to search
    if video_id and video_id in _bm25_indexes:
        video_ids_to_search = [video_id]
    elif video_id:
        # Video not indexed — return empty
        return []
    else:
        # Search all indexed videos
        video_ids_to_search = list(_bm25_indexes.keys())

    # Tokenize the query the same way we tokenized documents
    query_tokens = query.lower().split()

    for vid in video_ids_to_search:
        bm25 = _bm25_indexes[vid]
        chunks = _bm25_chunks[vid]

        # BM25 returns a score for every document
        scores = bm25.get_scores(query_tokens)

        for i, score in enumerate(scores):
            if score > 0:  # Only include documents with non-zero relevance
                chunk = chunks[i]
                results.append({
                    "text": chunk["text"],
                    "video_id": chunk["video_id"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "bm25_score": float(score),
                })

    # Sort by score descending and return top_k
    results.sort(key=lambda x: x["bm25_score"], reverse=True)

    return results[:top_k]


def is_video_indexed(video_id: str) -> bool:
    """Check if a video has a BM25 index."""
    return video_id in _bm25_indexes

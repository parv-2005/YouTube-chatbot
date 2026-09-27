"""
Retrieval Service — Hybrid Search with Reciprocal Rank Fusion
=============================================================

Combines vector search (Qdrant) and keyword search (BM25)
using Reciprocal Rank Fusion (RRF) for score normalization.

WHY NOT JUST ADD SCORES?
─────────────────────────
Vector search scores are cosine similarities: range [0, 1]
BM25 scores are TF-IDF based: range [0, ∞)

If we add them directly:
  vector: 0.85 + bm25: 12.4 = 13.25  (BM25 dominates)
  vector: 0.92 + bm25: 0.3  = 1.22   (much lower despite high semantic match)

This is misleading! The BM25 scale drowns out the vector signal.

RECIPROCAL RANK FUSION (RRF)
─────────────────────────────
Instead of using raw scores, RRF uses RANKS.

Formula:
  RRF_score(doc) = Σ 1 / (k + rank_i(doc))

Where:
  k = 60 (standard smoothing constant)
  rank_i = position of the document in retrieval source i

A document ranked #1 in vector search gets: 1/(60+1) = 0.0164
A document ranked #1 in BM25 gets:          1/(60+1) = 0.0164
Combined RRF score: 0.0328

This is FAIR because both sources contribute equally
regardless of their internal scoring scales.
"""

from typing import Optional

from app.services.vector_store import vector_search
from app.services.bm25_service import bm25_search
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def hybrid_search(
    query: str,
    top_k: int = 20,
    video_id: Optional[str] = None
) -> list[dict]:
    """
    Perform hybrid search combining vector and BM25 retrieval with RRF.

    Flow:
    1. Run vector search → get ranked results
    2. Run BM25 search → get ranked results
    3. Assign RRF scores based on rank positions
    4. Combine and sort by RRF score
    5. Return top_k results

    Args:
        query: User's search query
        top_k: Number of final results to return
        video_id: Optional filter for a specific video

    Returns:
        List of result dicts sorted by hybrid RRF score.
    """
    k = settings.RRF_K  # Smoothing constant (default: 60)

    # ── Step 1: Vector search (semantic) ──────────────────
    vector_results = vector_search(query, top_k=top_k, video_id=video_id)

    # ── Step 2: BM25 search (keyword) ─────────────────────
    keyword_results = bm25_search(query, top_k=top_k, video_id=video_id)

    # ── Step 3: Assign RRF scores ─────────────────────────
    # Use the chunk text as a unique key to merge results.
    # Each source contributes 1/(k + rank) to the RRF score.

    combined = {}

    # Process vector search results (ranked by cosine similarity)
    for rank, result in enumerate(vector_results, start=1):
        key = result["text"]
        rrf_contribution = 1.0 / (k + rank)

        combined[key] = {
            "text": result["text"],
            "video_id": result["video_id"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "vector_score": result.get("vector_score", 0),
            "bm25_score": 0,
            "vector_rank": rank,
            "bm25_rank": None,
            "rrf_score": rrf_contribution,
        }

    # Process BM25 results (ranked by keyword relevance)
    for rank, result in enumerate(keyword_results, start=1):
        key = result["text"]
        rrf_contribution = 1.0 / (k + rank)

        if key in combined:
            # Document found in BOTH sources — add RRF scores
            combined[key]["bm25_score"] = result.get("bm25_score", 0)
            combined[key]["bm25_rank"] = rank
            combined[key]["rrf_score"] += rrf_contribution
        else:
            # Document found only in BM25
            combined[key] = {
                "text": result["text"],
                "video_id": result["video_id"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "vector_score": 0,
                "bm25_score": result.get("bm25_score", 0),
                "vector_rank": None,
                "bm25_rank": rank,
                "rrf_score": rrf_contribution,
            }

    # ── Step 4: Sort by RRF score ─────────────────────────
    results = sorted(
        combined.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    logger.info(
        "hybrid_search_complete",
        query_preview=query[:50],
        vector_results=len(vector_results),
        bm25_results=len(keyword_results),
        combined_results=len(results),
        returned=min(top_k, len(results)),
    )

    return results[:top_k]

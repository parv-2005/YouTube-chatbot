"""
Reranker Service
================
Re-scores retrieval candidates using a cross-encoder model.

WHY TWO STAGES? (Retrieval vs. Reranking)
──────────────────────────────────────────
Retrieval (vector search + BM25):
  - FAST: Uses pre-computed indexes
  - APPROXIMATE: Encodes query and documents SEPARATELY
  - Scans the ENTIRE corpus efficiently
  - Returns top 20 candidates

Reranking (cross-encoder):
  - SLOW: Processes each (query, document) pair together
  - PRECISE: Reads both query and document through a transformer
  - Only runs on the TOP 20 candidates
  - Returns top 5 chunks

Why not just use the cross-encoder for everything?
  Running a cross-encoder on 1000+ chunks would be too slow.
  By first narrowing to 20 candidates, we get precise results
  without the computational cost.

WHY TOP 5?
──────────
  - LLMs have context windows, but quality matters more than quantity
  - Stuffing 20 chunks dilutes the signal with irrelevant text
  - The top 5 after reranking are the highest-quality, most relevant passages
  - This improves both answer quality AND token efficiency
"""

from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Load the cross-encoder model once.
# ms-marco-MiniLM-L-6-v2 is a good balance of speed and accuracy.
# It was trained on the MS MARCO passage ranking dataset.
_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(
    query: str,
    chunks: list[dict],
    top_k: int = 5
) -> list[dict]:
    """
    Re-score and re-rank retrieval candidates using a cross-encoder.

    The cross-encoder takes (query, chunk_text) pairs and produces
    a relevance score. Higher scores = more relevant.

    Args:
        query: The user's search query
        chunks: Retrieval candidates from hybrid search
        top_k: Number of top results to return (default: 5)

    Returns:
        Top-k chunks sorted by reranker score, with rerank_score added.
    """
    if not chunks:
        return []

    # Create (query, document) pairs for the cross-encoder.
    # The cross-encoder reads BOTH together through the transformer,
    # unlike bi-encoders which encode them separately.
    pairs = [
        [query, chunk["text"]]
        for chunk in chunks
    ]

    # Score all pairs at once (batched inference)
    scores = _reranker.predict(pairs)

    # Attach reranker scores to chunks
    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    # Sort by reranker score (descending)
    ranked = sorted(
        chunks,
        key=lambda x: x["rerank_score"],
        reverse=True,
    )

    logger.info(
        "reranking_complete",
        query_preview=query[:50],
        input_count=len(chunks),
        output_count=min(top_k, len(ranked)),
        best_score=round(ranked[0]["rerank_score"], 4) if ranked else 0,
    )

    return ranked[:top_k]

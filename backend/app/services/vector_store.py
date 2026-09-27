"""
Vector Store Service (Qdrant)
=============================
Manages the Qdrant vector database for semantic search.

Qdrant stores our text chunks as high-dimensional vectors.
When a user asks a question, we convert it to a vector
and find the most similar chunk vectors — this is "semantic search".

Key concepts:
- Collection: like a database table, holds all vectors
- Point: a single vector + its metadata (payload)
- Payload: the chunk text, video_id, timestamps stored alongside the vector
- Cosine similarity: measures how "close" two vectors are (0 = unrelated, 1 = identical)
"""

import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue
)

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.embedding_service import create_embedding, create_embeddings_batch

logger = get_logger(__name__)

# ── Qdrant Client ────────────────────────────────────────────
# In development: connects to a local Qdrant instance.
# In production: connect to Qdrant Cloud with an API key.
_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Get or create the Qdrant client singleton."""
    global _client

    if _client is None:
        # Use embedded local mode (stores data on disk, no server needed).
        # This is ideal for development without Docker.
        # In production, switch to host/port to connect to a Qdrant server.
        _client = QdrantClient(
            path=settings.QDRANT_PATH,
        )
        logger.info(
            "qdrant_connected_local",
            path=settings.QDRANT_PATH,
        )

    return _client


def ensure_collection():
    """
    Create the Qdrant collection if it doesn't exist.

    A collection defines:
    - Vector size (must match the embedding model's output dimension)
    - Distance metric (cosine similarity for text embeddings)
    """
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION_NAME

    # Check if collection already exists
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name not in existing_names:
        # We need the vector size from the embedding model.
        # Generate a test embedding to discover the dimension.
        test_vector = create_embedding("test")
        vector_size = len(test_vector)

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

        logger.info(
            "qdrant_collection_created",
            collection_name=collection_name,
            vector_size=vector_size
        )


def store_chunks(chunks: list[dict]) -> int:
    """
    Store text chunks as vectors in Qdrant.

    Each chunk becomes a "point" with:
    - A unique UUID
    - A vector (from the embedding model)
    - A payload (text, video_id, timestamps)

    Args:
        chunks: List of chunk dicts [{text, video_id, start_time, end_time}]

    Returns:
        Number of chunks stored.
    """
    client = get_qdrant_client()
    ensure_collection()

    # Batch-embed all chunk texts for efficiency
    texts = [chunk["text"] for chunk in chunks]
    vectors = create_embeddings_batch(texts)

    # Create Qdrant points
    points = []
    for chunk, vector in zip(chunks, vectors):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk["text"],
                    "video_id": chunk["video_id"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                },
            )
        )

    # Upsert in batches of 100 to avoid memory issues with large videos
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=batch,
        )

    logger.info(
        "chunks_stored_in_qdrant",
        chunk_count=len(points),
        collection=settings.QDRANT_COLLECTION_NAME
    )

    return len(points)


def vector_search(
    query: str,
    top_k: int = 20,
    video_id: Optional[str] = None
) -> list[dict]:
    """
    Semantic vector search using cosine similarity.

    Converts the query to a vector and finds the most similar
    chunk vectors in Qdrant.

    Args:
        query: User's search query
        top_k: Number of results to return
        video_id: Optional filter to search within a specific video

    Returns:
        List of result dicts with text, metadata, and similarity score.
    """
    client = get_qdrant_client()

    # Embed the query using the same model used for chunks
    query_vector = create_embedding(query)

    # Optional: filter results to a specific video
    query_filter = None
    if video_id:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="video_id",
                    match=MatchValue(value=video_id),
                )
            ]
        )

    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
    ).points

    return [
        {
            "text": result.payload["text"],
            "video_id": result.payload["video_id"],
            "start_time": result.payload["start_time"],
            "end_time": result.payload["end_time"],
            "vector_score": result.score,
        }
        for result in results
    ]


def get_all_chunks_for_video(video_id: str) -> list[dict]:
    """
    Retrieve all stored chunks for a specific video.
    Used to rebuild the BM25 index after a restart.
    """
    client = get_qdrant_client()

    results = client.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="video_id",
                    match=MatchValue(value=video_id),
                )
            ]
        ),
        limit=10000,
    )[0]  # scroll returns (points, next_page_offset)

    return [
        {
            "text": point.payload["text"],
            "video_id": point.payload["video_id"],
            "start_time": point.payload["start_time"],
            "end_time": point.payload["end_time"],
        }
        for point in results
    ]

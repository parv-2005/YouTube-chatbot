"""
Embedding Service
=================
Generates vector embeddings using Gemini's embedding model.

Embeddings convert text into numerical vectors that capture
semantic meaning. Similar concepts produce vectors that are
"close" in vector space, enabling semantic search.

We use Google's gemini-embedding-001 model which produces
768-dimensional vectors.
"""

import time

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Initialize the embedding model once.
# LangChain wraps the Google API call behind a simple interface.
embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.GOOGLE_API_KEY,
)

# ── Retry Configuration ─────────────────────────────────────
MAX_RETRIES = 5
INITIAL_BACKOFF = 2  # seconds


def _retry_with_backoff(func, *args, **kwargs):
    """
    Execute a function with exponential backoff on rate limit errors.
    Retries up to MAX_RETRIES times with increasing wait times.
    """
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "resource exhausted" in error_str

            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait_time = INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    "embedding_rate_limited",
                    attempt=attempt + 1,
                    wait_seconds=wait_time,
                )
                time.sleep(wait_time)
            else:
                raise


def create_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for a single text.

    Args:
        text: The text to embed.

    Returns:
        A list of floats (768-dimensional vector).
    """
    return _retry_with_backoff(embeddings_model.embed_query, text)


def create_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in a batch.

    Processes in sub-batches with small delays to avoid
    hitting the Gemini API rate limit (429 errors).

    Args:
        texts: List of texts to embed.

    Returns:
        List of embedding vectors.
    """
    logger.info("creating_embeddings_batch", count=len(texts))

    # Process in sub-batches to avoid rate limits
    # Gemini free tier has low RPM limits
    sub_batch_size = 5
    all_vectors = []

    for i in range(0, len(texts), sub_batch_size):
        batch = texts[i:i + sub_batch_size]

        vectors = _retry_with_backoff(
            embeddings_model.embed_documents, batch
        )
        all_vectors.extend(vectors)

        # Small delay between sub-batches to respect rate limits
        if i + sub_batch_size < len(texts):
            time.sleep(1)

    logger.info("embeddings_created", count=len(all_vectors))

    return all_vectors


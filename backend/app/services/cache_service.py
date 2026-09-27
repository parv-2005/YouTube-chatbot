"""
Cache Service (Redis)
=====================
Provides caching and rate limiting using Redis.

Redis is used for:
1. Caching expensive results (e.g., repeated identical queries)
2. Rate limiting API endpoints (e.g., auth endpoints)

Redis vs PostgreSQL:
  PostgreSQL = persistent structured data (users, conversations)
  Redis = fast temporary/cache data (query results, rate limits)

Redis stores data in-memory, so it's MUCH faster than a database
but data is not guaranteed to persist across restarts.
"""

import json
import time
from typing import Optional

import redis

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ── Redis Client ─────────────────────────────────────────────
_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """
    Get or create the Redis client.
    Returns None if Redis is unavailable (graceful degradation).
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        # Test the connection
        _redis_client.ping()
        logger.info("redis_connected", url=settings.REDIS_URL)
        return _redis_client

    except Exception as e:
        # Redis is optional — the app works without it,
        # just without caching and rate limiting.
        logger.warning("redis_unavailable", error=str(e))
        return None


# ── Caching ──────────────────────────────────────────────────

def cache_get(key: str) -> Optional[dict]:
    """
    Get a cached value by key.
    Returns None if not found or Redis is unavailable.
    """
    client = get_redis()
    if not client:
        return None

    try:
        value = client.get(f"cache:{key}")
        if value:
            return json.loads(value)
    except Exception:
        pass

    return None


def cache_set(key: str, value: dict, ttl_seconds: int = 300):
    """
    Cache a value with a time-to-live (TTL).

    Args:
        key: Cache key
        value: Data to cache (must be JSON-serializable)
        ttl_seconds: How long to keep the cached value (default: 5 minutes)
    """
    client = get_redis()
    if not client:
        return

    try:
        client.setex(
            f"cache:{key}",
            ttl_seconds,
            json.dumps(value),
        )
    except Exception as e:
        logger.warning("cache_set_failed", key=key, error=str(e))


# ── Rate Limiting ────────────────────────────────────────────
# Uses a sliding window approach:
# Track request timestamps in a sorted set,
# count how many are within the window.

def check_rate_limit(
    identifier: str,
    max_requests: int = None,
    window_seconds: int = None,
) -> bool:
    """
    Check if a request should be rate-limited.

    Args:
        identifier: Unique identifier (e.g., IP address, user ID)
        max_requests: Max requests allowed in the window
        window_seconds: Window size in seconds

    Returns:
        True if the request is ALLOWED, False if rate-limited.
    """
    client = get_redis()
    if not client:
        # If Redis is down, allow all requests
        return True

    max_req = max_requests or settings.RATE_LIMIT_REQUESTS
    window = window_seconds or settings.RATE_LIMIT_WINDOW

    key = f"ratelimit:{identifier}"
    now = time.time()
    window_start = now - window

    try:
        pipe = client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count requests in the current window
        pipe.zcard(key)

        # Add the current request
        pipe.zadd(key, {str(now): now})

        # Set expiry on the key
        pipe.expire(key, window)

        results = pipe.execute()
        request_count = results[1]

        if request_count >= max_req:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                count=request_count,
                limit=max_req,
            )
            return False

        return True

    except Exception as e:
        logger.warning("rate_limit_check_failed", error=str(e))
        return True  # Allow on error

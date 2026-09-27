"""
Structured Logging Configuration
=================================
Uses structlog for JSON-formatted, structured logs.

Why structured logging?
- Machine-parseable (JSON) for log aggregation tools
- Includes request IDs for tracing
- Consistent format across the entire application
- Easy to filter and search

What we log:
- Request metadata (method, path, status, duration)
- Ingestion pipeline progress
- Retrieval and reranking metrics
- LLM latency
- Errors with context

What we NEVER log:
- API keys
- Passwords
- JWT secrets
- Sensitive user data
"""

import logging
import sys

import structlog

from app.core.config import settings


def setup_logging():
    """
    Configure structlog for the entire application.
    In development, outputs human-readable colored logs.
    In production, outputs JSON for log aggregation.
    """

    # Determine if we're in development mode
    is_development = settings.LOG_LEVEL == "DEBUG"

    # Shared processors that run on every log entry
    shared_processors = [
        # Add log level as a string (e.g., "info", "error")
        structlog.stdlib.add_log_level,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # Add caller information (file, function, line)
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if is_development:
        # Human-readable colored output for development
        renderer = structlog.dev.ConsoleRenderer()
    else:
        # JSON output for production log aggregation
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            # Format the final output
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the standard library logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str = __name__):
    """Get a structlog logger instance with a bound name."""
    return structlog.get_logger(name)

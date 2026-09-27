"""
FastAPI Application — Main Entry Point
=======================================
This is the root of the entire backend application.

It sets up:
1. FastAPI app with metadata for documentation
2. CORS middleware (allows frontend to call the API)
3. Lifespan events (startup/shutdown)
4. Global exception handling
5. API router with /api prefix
6. Health check endpoint

To run (development):
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.database.session import create_tables
from app.api.router import api_router


# ── Logging Setup ────────────────────────────────────────────
setup_logging()
logger = get_logger(__name__)


# ── Lifespan ─────────────────────────────────────────────────
# Lifespan events run code at startup and shutdown.
# We use this to create database tables on startup.

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup:
    - Create database tables (development convenience)
    - Log that the application is ready

    Shutdown:
    - Clean up resources
    """
    # ── Startup ──────────────────────────────────────────
    logger.info("application_starting", project=settings.PROJECT_NAME)

    # Create database tables if they don't exist.
    # In production, you would use Alembic migrations instead.
    create_tables()
    logger.info("database_tables_created")

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────
    logger.info("application_shutting_down")


# ── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "An industrial-level YouTube chatbot powered by "
        "RAG, LangGraph, and Gemini."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS Middleware ──────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) controls which domains
# can call our API. Without this, the browser blocks requests
# from the Next.js frontend (different port = different origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ────────────────────────────────
# Catches unhandled exceptions and returns a clean error response.
# NEVER exposes stack traces to users (security risk).

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler.
    Logs the full error internally but returns a generic message to the client.
    """
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again."},
    )


# ── Include API Router ──────────────────────────────────────
# All API endpoints are prefixed with /api
app.include_router(api_router, prefix="/api")


# ── Health Check ─────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "healthy", "project": settings.PROJECT_NAME}

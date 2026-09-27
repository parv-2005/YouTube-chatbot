"""
API Router
==========
Aggregates all sub-routers into a single API router.
Each sub-router handles a specific domain (auth, videos, chat, etc.).
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.videos import router as videos_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router

# Main API router — all sub-routers are included here.
# The prefix "/api" is added in main.py when including this router.
api_router = APIRouter()

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    videos_router,
    prefix="/videos",
    tags=["Videos"],
)

api_router.include_router(
    chat_router,
    prefix="/chat",
    tags=["Chat"],
)

api_router.include_router(
    conversations_router,
    prefix="/conversations",
    tags=["Conversations"],
)

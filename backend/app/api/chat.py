"""
Chat API
========
Endpoints for the RAG chatbot.

Supports:
1. Regular chat (POST /chat) — full response
2. Streaming chat (POST /chat/stream) — Server-Sent Events (SSE)

Why streaming?
  Without streaming, the user waits 3-5 seconds staring at a blank screen.
  With streaming, they see the answer being typed out in real-time.
  This dramatically improves perceived performance and user experience.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.database.models import User, Conversation, Video
from app.schemas.chat import ChatRequest, ChatResponse, SourceReference
from app.services.rag_graph import rag_graph
from app.services.memory_service import get_conversation_history, save_message
from app.services.llm_service import generate_answer_stream
from app.services.retrieval_service import hybrid_search
from app.services.reranker_service import rerank
from app.utils.timestamp_utils import seconds_to_timestamp, build_timestamp_link
from app.services.cache_service import cache_get, cache_set
from app.core.config import settings
from app.core.logging_config import get_logger
from langchain_core.documents import Document

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message and receive a complete RAG-powered answer.

    Flow:
    1. Validate the conversation exists and belongs to the user
    2. Load conversation history for follow-up support
    3. Run the LangGraph RAG workflow
    4. Save both user and assistant messages
    5. Return the answer with source references
    """
    # Validate conversation ownership
    conversation = _validate_conversation(data.conversation_id, current_user, db)

    # Get the video ID for scoped retrieval
    video = db.query(Video).filter(Video.id == conversation.video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated video not found",
        )

    # Load conversation history for follow-up question support
    chat_history = get_conversation_history(db, str(data.conversation_id))

    # Save the user's message
    save_message(db, str(data.conversation_id), "user", data.message)

    # Check cache for identical queries
    cache_key = f"{video.youtube_video_id}:{data.message}"
    cached = cache_get(cache_key)
    if cached:
        logger.info("cache_hit", query=data.message[:50])
        # Still save the cached answer as a message
        save_message(
            db, str(data.conversation_id), "assistant",
            cached["answer"], cached["sources"]
        )
        return ChatResponse(
            answer=cached["answer"],
            sources=[SourceReference(**s) for s in cached["sources"]],
        )

    # Run the LangGraph RAG workflow
    result = rag_graph.invoke({
        "question": data.message,
        "standalone_query": "",
        "chat_history": chat_history,
        "video_id": video.youtube_video_id,
        "documents": [],
        "answer": "",
        "sources": [],
        "retry_count": 0,
    })

    answer = result["answer"]
    sources = result.get("sources", [])

    # Build source references with timestamp links
    source_refs = [
        SourceReference(
            text=s["text"],
            video_id=s["video_id"],
            start_time=s["start_time"],
            end_time=s["end_time"],
            timestamp_label=s["timestamp_label"],
            timestamp_link=s["timestamp_link"],
        )
        for s in sources
    ]

    # Save the assistant's response
    save_message(db, str(data.conversation_id), "assistant", answer, sources)

    # Cache the result for repeated queries
    cache_set(cache_key, {"answer": answer, "sources": sources}, ttl_seconds=600)

    # Auto-title the conversation from the first question
    if conversation.title == "New Conversation":
        conversation.title = data.message[:80]
        db.commit()

    return ChatResponse(answer=answer, sources=source_refs)


@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message and receive a streaming response via Server-Sent Events (SSE).

    SSE (Server-Sent Events):
    - A standard HTTP protocol for server-to-client streaming
    - The server keeps the connection open and sends data chunks
    - Each chunk is prefixed with "data: " and followed by two newlines
    - The client uses EventSource or fetch() to read the stream

    This endpoint returns tokens one at a time as Gemini generates them,
    followed by a final event with the source references.
    """
    # Validate conversation ownership
    conversation = _validate_conversation(data.conversation_id, current_user, db)

    video = db.query(Video).filter(Video.id == conversation.video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated video not found",
        )

    chat_history = get_conversation_history(db, str(data.conversation_id))
    save_message(db, str(data.conversation_id), "user", data.message)

    # Retrieve documents for context (same as non-streaming)
    candidates = hybrid_search(
        data.message,
        top_k=settings.RETRIEVAL_TOP_K,
        video_id=video.youtube_video_id,
    )
    reranked = rerank(data.message, candidates, top_k=settings.RERANK_TOP_K)

    documents = []
    sources = []
    for chunk in reranked:
        ts_label = seconds_to_timestamp(chunk["start_time"])
        ts_link = build_timestamp_link(chunk["video_id"], chunk["start_time"])

        documents.append(
            Document(
                page_content=chunk["text"],
                metadata={
                    "video_id": chunk["video_id"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "timestamp_label": ts_label,
                    "timestamp_link": ts_link,
                    "rerank_score": chunk.get("rerank_score", 0),
                },
            )
        )

        sources.append({
            "text": chunk["text"][:200],
            "video_id": chunk["video_id"],
            "start_time": chunk["start_time"],
            "end_time": chunk["end_time"],
            "timestamp_label": ts_label,
            "timestamp_link": ts_link,
        })

    def event_stream():
        """Generator that yields SSE-formatted events."""
        full_answer = ""

        # Stream tokens from Gemini
        for token in generate_answer_stream(
            data.message, documents, chat_history
        ):
            full_answer += token
            yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"

        # Final event with sources
        yield f"data: {json.dumps({'token': '', 'done': True, 'sources': sources})}\n\n"

        # Save the complete answer
        save_message(
            db, str(data.conversation_id), "assistant", full_answer, sources
        )

        # Auto-title
        if conversation.title == "New Conversation":
            conversation.title = data.message[:80]
            db.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def _validate_conversation(conversation_id, current_user, db) -> Conversation:
    """Validate that the conversation exists and belongs to the current user."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation

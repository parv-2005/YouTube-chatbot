"""
Conversations API
=================
CRUD endpoints for managing conversations.
Each conversation is scoped to a user + video pair.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.dependencies import get_db, get_current_user
from app.database.models import User, Conversation, Message, Video
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListItem,
    ConversationListResponse,
    MessageResponse,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation for a specific video."""
    # Verify the video exists and is ready
    video = db.query(Video).filter(Video.id == data.video_id).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video is not ready (status: {video.status})",
        )

    conversation = Conversation(
        user_id=current_user.id,
        video_id=data.video_id,
        title=data.title or "New Conversation",
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    logger.info(
        "conversation_created",
        conversation_id=str(conversation.id),
        video_id=str(data.video_id),
    )

    return ConversationResponse(
        id=conversation.id,
        video_id=conversation.video_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        video_title=video.title,
        messages=[],
    )


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all conversations for the current user."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    items = []
    for conv in conversations:
        # Get the video title
        video = db.query(Video).filter(Video.id == conv.video_id).first()
        video_title = video.title if video else None

        # Count messages
        msg_count = db.query(func.count(Message.id)).filter(
            Message.conversation_id == conv.id
        ).scalar()

        items.append(
            ConversationListItem(
                id=conv.id,
                video_id=conv.video_id,
                title=conv.title,
                video_title=video_title,
                message_count=msg_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )

    return ConversationListResponse(
        conversations=items,
        total=len(items),
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a conversation with all its messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    video = db.query(Video).filter(Video.id == conversation.video_id).first()

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return ConversationResponse(
        id=conversation.id,
        video_id=conversation.video_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        video_title=video.title if video else None,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sources=msg.sources,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    db.delete(conversation)
    db.commit()

    logger.info(
        "conversation_deleted",
        conversation_id=conversation_id,
    )

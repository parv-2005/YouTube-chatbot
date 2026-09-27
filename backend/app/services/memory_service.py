"""
Memory Service
==============
Manages conversation memory for follow-up question support.

Development: loads recent messages from PostgreSQL.
Each conversation's history is stored as Message records.

Why memory matters:
  Without memory, the system can't understand:
    "Why is IT useful?" (what is "it"?)
    "Can you explain more?" (about what?)
    "Give me an example of THAT." (of what?)

  With memory, the query_analysis node in LangGraph
  rewrites these into standalone questions before retrieval.
"""

from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from app.database.models import Message, Conversation
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_conversation_history(
    db: Session,
    conversation_id: str,
    max_messages: int = 10,
) -> list:
    """
    Load recent messages from a conversation.

    Returns LangChain message objects (HumanMessage / AIMessage)
    for use with the LLM service.

    We limit to the last `max_messages` to prevent the prompt
    from becoming too long and expensive.

    Args:
        db: Database session
        conversation_id: UUID of the conversation
        max_messages: Maximum number of messages to return

    Returns:
        List of LangChain message objects.
    """
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(max_messages)
        .all()
    )

    # Reverse to get chronological order (oldest first)
    messages.reverse()

    # Convert to LangChain message format
    history = []
    for msg in messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            history.append(AIMessage(content=msg.content))

    logger.info(
        "loaded_conversation_history",
        conversation_id=str(conversation_id),
        message_count=len(history),
    )

    return history


def save_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    sources: list = None,
):
    """
    Save a message to the conversation history.

    Args:
        db: Database session
        conversation_id: UUID of the conversation
        role: 'user' or 'assistant'
        content: Message text
        sources: Source references (for assistant messages)
    """
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
    )

    db.add(message)

    # Also update the conversation's updated_at timestamp
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if conversation:
        from datetime import datetime, timezone
        conversation.updated_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(
        "message_saved",
        conversation_id=str(conversation_id),
        role=role,
        content_length=len(content),
    )

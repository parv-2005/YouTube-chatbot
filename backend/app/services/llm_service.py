"""
LLM Service (Gemini)
====================
Wraps Google's Gemini LLM with LangChain for:

1. Answer generation (RAG)
2. Query rewriting (for follow-up questions)
3. Streaming responses

LangChain provides:
- ChatPromptTemplate: structured prompt construction
- Runnable chains: composable prompt → LLM pipelines
- Streaming: token-by-token output for real-time UX
"""

from typing import Generator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# ── Initialize the Gemini LLM ───────────────────────────────
# temperature=0 makes the model more deterministic and factual.
# This is important for RAG — we want the model to stick to
# the provided context rather than being creative.
llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0,
    streaming=True,
)


# ── RAG Answer Prompt ───────────────────────────────────────
# This prompt template instructs Gemini to:
# 1. Only use information from the provided context
# 2. Cite which part of the context it's using
# 3. Admit when information is not available
RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful YouTube video assistant. Your job is to answer
questions about a specific YouTube video using ONLY the provided
transcript excerpts as context.

RULES:
1. Answer ONLY based on the provided context.
2. If the answer is not in the context, say: "I couldn't find
   information about that in this video."
3. Be concise but thorough.
4. Reference timestamps when relevant (e.g., "Around 01:12, the
   speaker explains...").
5. Use natural, conversational language.

CONTEXT (transcript excerpts):
{context}

CHAT HISTORY:
{chat_history}

USER'S QUESTION:
{question}

YOUR ANSWER:
""")

# Create a runnable chain: prompt → LLM
# This is a LangChain "chain" — a composable pipeline.
# When invoked, it fills the prompt template and sends it to Gemini.
rag_chain = RAG_PROMPT | llm


# ── Query Rewriting Prompt ──────────────────────────────────
# Used when the user asks a follow-up question that references
# previous messages (e.g., "Why is IT useful?" where "it" refers
# to something mentioned earlier).
REWRITE_PROMPT = ChatPromptTemplate.from_template("""
Given the following conversation history and a follow-up question,
rewrite the follow-up question to be a STANDALONE question that
can be understood without the conversation history.

The rewritten question should be clear, specific, and optimized
for searching a YouTube video transcript.

CHAT HISTORY:
{chat_history}

FOLLOW-UP QUESTION:
{question}

STANDALONE QUESTION (return ONLY the rewritten question, nothing else):
""")

rewrite_chain = REWRITE_PROMPT | llm


def generate_answer(
    question: str,
    documents: list[Document],
    chat_history: list = None,
) -> str:
    """
    Generate an answer using the RAG chain.

    Constructs context from retrieved documents and invokes Gemini.

    Args:
        question: The user's question
        documents: Retrieved and reranked document chunks
        chat_history: Previous messages for context

    Returns:
        The generated answer text.
    """
    # Build context from documents
    context = "\n\n---\n\n".join(
        f"[{doc.metadata.get('timestamp_label', '')}] {doc.page_content}"
        for doc in documents
    )

    # Format chat history as a readable string
    history_str = _format_chat_history(chat_history or [])

    logger.info(
        "generating_answer",
        question_preview=question[:50],
        context_chunks=len(documents),
    )

    response = rag_chain.invoke({
        "context": context,
        "chat_history": history_str,
        "question": question,
    })

    return response.content


def generate_answer_stream(
    question: str,
    documents: list[Document],
    chat_history: list = None,
) -> Generator[str, None, None]:
    """
    Generate an answer with streaming (token by token).

    This enables real-time UX — the user sees the answer
    being typed out rather than waiting for the full response.

    Yields individual tokens as they're generated.
    """
    context = "\n\n---\n\n".join(
        f"[{doc.metadata.get('timestamp_label', '')}] {doc.page_content}"
        for doc in documents
    )

    history_str = _format_chat_history(chat_history or [])

    logger.info(
        "streaming_answer",
        question_preview=question[:50],
        context_chunks=len(documents),
    )

    # stream() returns chunks of the response as they're generated
    for chunk in rag_chain.stream({
        "context": context,
        "chat_history": history_str,
        "question": question,
    }):
        if chunk.content:
            yield chunk.content


def rewrite_query(
    question: str,
    chat_history: list = None,
) -> str:
    """
    Rewrite a follow-up question into a standalone question.

    Example:
        History: [User: "What is RAG?", AI: "RAG means..."]
        Question: "Why is it useful?"
        Rewritten: "Why is Retrieval-Augmented Generation (RAG) useful?"

    This ensures the retrieval system can find relevant chunks
    even for questions that use pronouns or references.
    """
    history_str = _format_chat_history(chat_history or [])

    response = rewrite_chain.invoke({
        "chat_history": history_str,
        "question": question,
    })

    rewritten = response.content.strip()

    logger.info(
        "query_rewritten",
        original=question[:50],
        rewritten=rewritten[:50],
    )

    return rewritten


def _format_chat_history(chat_history: list) -> str:
    """Format chat history messages into a readable string."""
    if not chat_history:
        return "No previous conversation."

    lines = []
    for msg in chat_history[-6:]:  # Last 6 messages (3 exchanges)
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Assistant: {msg.content}")
        elif isinstance(msg, dict):
            lines.append(f"{msg.get('role', 'User')}: {msg.get('content', '')}")

    return "\n".join(lines)

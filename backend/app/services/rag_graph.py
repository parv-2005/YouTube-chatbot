"""
RAG Graph — LangGraph Agentic Workflow
======================================
The brain of the chatbot. Uses LangGraph to orchestrate
the complete RAG pipeline with conditional routing.

LANGGRAPH CONCEPTS:
─────────────────────
State:       A TypedDict that holds all data flowing through the graph.
             Each node reads from and writes to this shared state.

Node:        A Python function that performs one step of the pipeline.
             Receives the current state, returns state updates.

Edge:        Connects nodes in sequence (A → B).

Conditional Edge:
             Routes to different nodes based on a condition.
             Example: if documents are relevant → answer;
                      if not → rewrite query and retry.

START / END: Special nodes marking the graph's entry and exit points.

Graph Compilation:
             builder.compile() validates the graph structure and
             creates an executable workflow.

GRAPH STRUCTURE:
────────────────
START
  │
  ▼
query_analysis   ← Rewrites follow-up questions into standalone queries
  │
  ▼
retrieve         ← Hybrid search (vector + BM25 + RRF) → Reranker → Top 5
  │
  ▼
check_relevance  ← Are the retrieved documents actually relevant?
  │
  ├── "answer"   → answer_node → END
  │
  └── "rewrite"  → rewrite_node → retrieve (retry with better query)
"""

from typing import TypedDict, List, Optional
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END

from app.services.retrieval_service import hybrid_search
from app.services.reranker_service import rerank
from app.services.llm_service import (
    generate_answer,
    generate_answer_stream,
    rewrite_query,
)
from app.utils.timestamp_utils import (
    seconds_to_timestamp,
    build_timestamp_link,
)
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# ── Graph State ──────────────────────────────────────────────
# This TypedDict defines ALL data that flows through the graph.
# Each node can read any field and return updates to any field.

class GraphState(TypedDict):
    question: str               # Original user question
    standalone_query: str       # Rewritten standalone query (no pronouns)
    chat_history: list          # Previous messages for follow-up context
    video_id: Optional[str]     # Filter retrieval to a specific video
    documents: List[Document]   # Retrieved + reranked documents
    answer: str                 # Final generated answer
    sources: list               # Source chunks with timestamps
    retry_count: int            # Prevents infinite rewrite loops


# ── Node 1: Query Analysis ──────────────────────────────────
# Resolves follow-up questions by examining chat history.
# "Why is IT useful?" → "Why is Retrieval-Augmented Generation useful?"

def query_analysis_node(state: GraphState) -> dict:
    """
    Analyze the user's question and produce a standalone search query.

    If there's chat history, the question might contain pronouns
    or references ("it", "that", "this") that need resolution.
    The LLM rewrites the question to be self-contained.

    If there's no chat history, the question is used as-is.
    """
    question = state["question"]
    chat_history = state.get("chat_history", [])

    if chat_history:
        # Rewrite the question to resolve references
        standalone = rewrite_query(question, chat_history)
    else:
        # First question in the conversation — use as-is
        standalone = question

    logger.info(
        "query_analysis_complete",
        original=question[:50],
        standalone=standalone[:50],
        had_history=bool(chat_history),
    )

    return {"standalone_query": standalone}


# ── Node 2: Retrieve ────────────────────────────────────────
# Runs the full retrieval pipeline:
# Hybrid Search (Vector + BM25 + RRF) → Cross-Encoder Reranker → Top 5

def retrieve_node(state: GraphState) -> dict:
    """
    Retrieve the most relevant transcript chunks for the query.

    Pipeline:
    1. Hybrid search: vector (semantic) + BM25 (keyword) + RRF fusion
       → Top 20 candidates
    2. Cross-encoder reranking: precise relevance scoring
       → Top 5 chunks
    3. Convert to LangChain Documents with metadata
    """
    query = state["standalone_query"]
    video_id = state.get("video_id")

    # Step 1: Hybrid retrieval with RRF → top 20
    # We retrieve 20 candidates because the reranker needs a
    # larger pool to select the truly best 5 chunks.
    candidates = hybrid_search(
        query,
        top_k=settings.RETRIEVAL_TOP_K,
        video_id=video_id,
    )

    # Step 2: Rerank → top 5
    reranked = rerank(
        query,
        candidates,
        top_k=settings.RERANK_TOP_K,
    )

    # Step 3: Convert to LangChain Documents
    # Documents carry both the text and metadata (timestamps, video_id).
    documents = []
    for chunk in reranked:
        timestamp_label = seconds_to_timestamp(chunk["start_time"])
        timestamp_link = build_timestamp_link(
            chunk["video_id"], chunk["start_time"]
        )

        documents.append(
            Document(
                page_content=chunk["text"],
                metadata={
                    "video_id": chunk["video_id"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "timestamp_label": timestamp_label,
                    "timestamp_link": timestamp_link,
                    "rerank_score": chunk.get("rerank_score", 0),
                },
            )
        )

    logger.info(
        "retrieval_complete",
        query_preview=query[:50],
        candidates=len(candidates),
        reranked=len(documents),
    )

    return {"documents": documents}


# ── Node 3: Check Relevance (Conditional) ───────────────────
# Decides whether the retrieved documents are good enough to answer,
# or if we should try rewriting the query.

def check_relevance(state: GraphState) -> str:
    """
    Conditional edge: decide whether to answer or rewrite.

    Returns:
      "answer"  → if documents are relevant enough
      "rewrite" → if documents are poor/empty (will retry)

    Guard against infinite loops:
      After 2 retries, always proceed to answer (even with poor docs).
      The answer node will say "I couldn't find information..."
    """
    retry_count = state.get("retry_count", 0)
    documents = state.get("documents", [])

    # Safety: max 2 retries to prevent infinite loops
    if retry_count >= 2:
        logger.info("max_retries_reached", retry_count=retry_count)
        return "generate_answer"

    # No documents found at all → try rewriting the query
    if not documents:
        logger.info("no_documents_found", action="rewrite")
        return "rewrite"

    # Check the best rerank score. Cross-encoder scores > 0
    # generally indicate some relevance. Below -2 is very poor.
    best_score = max(
        doc.metadata.get("rerank_score", 0) for doc in documents
    )

    if best_score < -2.0:
        logger.info(
            "low_relevance_score",
            best_score=round(best_score, 4),
            action="rewrite"
        )
        return "rewrite"

    return "generate_answer"


# ── Node 4: Rewrite Query ───────────────────────────────────
# When retrieval produces poor results, we rephrase the query
# and try again. This gives the system a second chance.

def rewrite_node(state: GraphState) -> dict:
    """
    Rewrite the standalone query for better retrieval results.

    Uses the LLM to generate an alternative phrasing that might
    match different chunks in the transcript.
    """
    original = state["standalone_query"]

    rewritten = rewrite_query(
        f"Try a different phrasing: {original}",
        state.get("chat_history", []),
    )

    retry_count = state.get("retry_count", 0) + 1

    logger.info(
        "query_rewritten_for_retry",
        original=original[:50],
        rewritten=rewritten[:50],
        retry_count=retry_count,
    )

    return {
        "standalone_query": rewritten,
        "retry_count": retry_count,
    }


# ── Node 5: Answer ──────────────────────────────────────────
# Generates the final answer using Gemini with the retrieved context.

def answer_node(state: GraphState) -> dict:
    """
    Generate the final answer and extract source references.

    Uses the LLM service to create an answer grounded in
    the retrieved document context.
    """
    documents = state.get("documents", [])
    question = state["question"]
    chat_history = state.get("chat_history", [])

    # Generate the answer
    answer = generate_answer(question, documents, chat_history)

    # Extract source references for the frontend
    sources = [
        {
            "text": doc.page_content[:200],  # Truncate for display
            "video_id": doc.metadata["video_id"],
            "start_time": doc.metadata["start_time"],
            "end_time": doc.metadata["end_time"],
            "timestamp_label": doc.metadata["timestamp_label"],
            "timestamp_link": doc.metadata["timestamp_link"],
        }
        for doc in documents
    ]

    logger.info(
        "answer_generated",
        answer_length=len(answer),
        source_count=len(sources),
    )

    return {
        "answer": answer,
        "sources": sources,
    }


# ── Build the Graph ─────────────────────────────────────────
# StateGraph manages the flow between nodes.
# Each node is a function that receives state and returns updates.

builder = StateGraph(GraphState)

# Register nodes
builder.add_node("query_analysis", query_analysis_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("rewrite", rewrite_node)
builder.add_node("generate_answer", answer_node)

# Define edges (the flow between nodes)

# START → Query Analysis
builder.add_edge(START, "query_analysis")

# Query Analysis → Retrieve
builder.add_edge("query_analysis", "retrieve")

# Retrieve → Check Relevance (conditional routing)
builder.add_conditional_edges(
    "retrieve",
    check_relevance,
    {
        "generate_answer": "generate_answer",    # Good documents → generate answer
        "rewrite": "rewrite",  # Poor documents → try different query
    },
)

# Rewrite → Retrieve (retry loop)
builder.add_edge("rewrite", "retrieve")

# Answer → END
builder.add_edge("generate_answer", END)

# Compile the graph into an executable workflow.
# After compilation, the graph validates that:
# - All nodes are reachable
# - All edges point to valid nodes
# - There are no disconnected subgraphs
rag_graph = builder.compile()

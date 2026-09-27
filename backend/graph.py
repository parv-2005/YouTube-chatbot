from typing import TypedDict, List

from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END

from retriever import retrieve
from llm import answer_question, llm


# -------------------------
# Graph State
# -------------------------

class GraphState(TypedDict):
    question: str
    documents: List[Document]
    answer: str
    chat_history: list


# -------------------------
# Retrieve Node
# -------------------------

def retrieve_node(state: GraphState):

    documents = retrieve(state["question"])

    return {
        "documents": documents
    }


# -------------------------
# Relevance Check
# -------------------------

def check_relevance(state: GraphState):

    if not state["documents"]:
        return "rewrite"

    return "answer"


# -------------------------
# Rewrite Node
# -------------------------

def rewrite_node(state: GraphState):

    question = state["question"]

    prompt = f"""
Rewrite the following question to make it clearer
for searching a YouTube transcript.

Original question:
{question}

Return only the rewritten question.
"""

    response = llm.invoke(prompt)

    return {
        "question": response.content
    }


# -------------------------
# Answer Node
# -------------------------

def answer_node(state: GraphState):

    answer = answer_question(
        state["question"],
        state["documents"]
    )

    return {
        "answer": answer
    }


# -------------------------
# Build Graph
# -------------------------

builder = StateGraph(GraphState)

builder.add_node("retrieve", retrieve_node)
builder.add_node("rewrite", rewrite_node)
builder.add_node("answer", answer_node)


# START → Retrieve
builder.add_edge(
    START,
    "retrieve"
)


# Retrieve → Answer OR Rewrite
builder.add_conditional_edges(
    "retrieve",
    check_relevance,
    {
        "answer": "answer",
        "rewrite": "rewrite"
    }
)


# Rewrite → Retrieve
builder.add_edge(
    "rewrite",
    "retrieve"
)


# Answer → END
builder.add_edge(
    "answer",
    END
)


# Compile
graph = builder.compile()
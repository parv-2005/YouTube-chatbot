from fastapi import FastAPI
from youtube import get_transcript, get_video_id
from chunking import create_chunks
from embeddings import create_embedding
from vector_store import store_chunks, hybrid_search
from reranker import rerank
from llm import generate_answer
from llm import answer_question
from graph import graph

app = FastAPI(title="YouTube Chatbot API")


@app.get("/")
def home():
    return {"message": "YouTube Chatbot Backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/transcript")
def transcript(url: str):
    return get_transcript(url)


@app.get("/chunks")
def chunks(url: str):
    video_id = get_video_id(url)

    if not video_id:
        return {"error": "Invalid YouTube URL"}

    transcript_data = get_transcript(url)

    if isinstance(transcript_data, dict):
        return transcript_data

    return create_chunks(transcript_data, video_id)


@app.get("/embedding")
def embedding(text: str):
    vector = create_embedding(text)

    return {
        "dimensions": len(vector),
        "vector": vector
    }


@app.post("/store")
def store(url: str):
    video_id = get_video_id(url)

    if not video_id:
        return {"error": "Invalid YouTube URL"}

    transcript_data = get_transcript(url)

    if isinstance(transcript_data, dict):
        return transcript_data

    chunks_data = create_chunks(
        transcript_data,
        video_id
    )

    count = store_chunks(chunks_data)

    return {
        "message": "Chunks stored successfully",
        "chunks": count
    }


@app.get("/search")
def search(query: str):

    # Step 1: Hybrid retrieval → Top 20
    results = hybrid_search(query, top_k=20)

    # Step 2: Rerank → Top 5
    results = rerank(
        query,
        results,
        top_k=5
    )

    return {
        "query": query,
        "results": results
    }

@app.get("/chat")
def chat(query: str):

    result = graph.invoke({
        "question": query,
        "documents": [],
        "answer": ""
    })

    return {
        "question": query,
        "answer": result["answer"],
        "sources": [
            {
                "text": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in result["documents"]
        ]
    }
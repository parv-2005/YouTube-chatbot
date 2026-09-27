from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from embeddings import embeddings
from rank_bm25 import BM25Okapi
import uuid


client = QdrantClient(":memory:")

COLLECTION_NAME = "youtube_transcripts"

# Keep chunks for BM25
all_chunks = []
bm25 = None


def create_collection():
    vector_size = len(
        embeddings.embed_query("test")
    )

    collections = client.get_collections().collections

    if COLLECTION_NAME not in [c.name for c in collections]:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )


def store_chunks(chunks):
    global all_chunks, bm25

    create_collection()

    points = []

    for chunk in chunks:
        vector = embeddings.embed_query(chunk["text"])

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=chunk
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

    # Store chunks for BM25
    all_chunks.extend(chunks)

    tokenized_docs = [
        chunk["text"].lower().split()
        for chunk in all_chunks
    ]

    bm25 = BM25Okapi(tokenized_docs)

    return len(points)


def vector_search(query, top_k=20):
    query_vector = embeddings.embed_query(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k
    ).points

    return [
        {
            "text": result.payload["text"],
            "video_id": result.payload["video_id"],
            "start_time": result.payload["start_time"],
            "end_time": result.payload["end_time"],
            "score": result.score
        }
        for result in results
    ]


def bm25_search(query, top_k=20):
    if not all_chunks or bm25 is None:
        return []

    query_tokens = query.lower().split()

    scores = bm25.get_scores(query_tokens)

    ranked_indexes = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    results = []

    for i in ranked_indexes:
        chunk = all_chunks[i]

        results.append({
            "text": chunk["text"],
            "video_id": chunk["video_id"],
            "start_time": chunk["start_time"],
            "end_time": chunk["end_time"],
            "score": float(scores[i])
        })

    return results


def hybrid_search(query, top_k=20):
    vector_results = vector_search(query, top_k)
    keyword_results = bm25_search(query, top_k)

    combined = {}

    # Add vector results
    for result in vector_results:
        key = result["text"]

        combined[key] = {
            **result,
            "vector_score": result["score"],
            "bm25_score": 0
        }

    # Add BM25 results
    for result in keyword_results:
        key = result["text"]

        if key in combined:
            combined[key]["bm25_score"] = result["score"]
        else:
            combined[key] = {
                **result,
                "vector_score": 0,
                "bm25_score": result["score"]
            }

    # Simple combined score
    for result in combined.values():
        result["hybrid_score"] = (
            result["vector_score"] +
            result["bm25_score"]
        )

    results = sorted(
        combined.values(),
        key=lambda x: x["hybrid_score"],
        reverse=True
    )

    return results[:top_k]
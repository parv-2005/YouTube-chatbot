from vector_store import hybrid_search
from reranker import rerank
from langchain_core.documents import Document


def retrieve(query, top_k=5):

    results = hybrid_search(query, top_k=20)

    results = rerank(
        query,
        results,
        top_k=top_k
    )

    documents = []

    for result in results:
        documents.append(
            Document(
                page_content=result["text"],
                metadata={
                    "video_id": result["video_id"],
                    "start_time": result["start_time"],
                    "end_time": result["end_time"]
                }
            )
        )

    return documents
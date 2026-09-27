from sentence_transformers import CrossEncoder


model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank(query, chunks, top_k=5):

    if not chunks:
        return []

    pairs = [
        [query, chunk["text"]]
        for chunk in chunks
    ]

    scores = model.predict(pairs)

    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    ranked_chunks = sorted(
        chunks,
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return ranked_chunks[:top_k]
"""
Ragas Evaluation Script
=======================
Evaluates the RAG pipeline quality using the Ragas framework.

Ragas Metrics Explained:
─────────────────────────
Faithfulness:
  Does the answer ONLY use information from the provided context?
  High = answer is grounded in retrieved chunks (no hallucination)
  Low = answer contains information not in the context

Answer Relevancy:
  Is the answer relevant to the question?
  High = directly addresses what was asked
  Low = tangential or off-topic

Context Precision:
  Are the retrieved chunks actually relevant to the question?
  High = retrieved chunks contain useful information
  Low = retrieved chunks are mostly noise

Context Recall:
  Did we retrieve ALL the relevant information?
  High = important information was not missed
  Low = some relevant chunks were not retrieved

USAGE:
  python -m evaluation.evaluate

REQUIREMENTS:
  - Backend services must be running (Qdrant, etc.)
  - A video must be ingested first
  - GOOGLE_API_KEY must be set
"""

import json
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def load_test_dataset(path: str = None) -> list[dict]:
    """Load the evaluation test dataset."""
    if path is None:
        path = os.path.join(
            os.path.dirname(__file__),
            "test_dataset.json"
        )

    with open(path) as f:
        return json.load(f)


def run_evaluation():
    """
    Run Ragas evaluation on the test dataset.

    Steps:
    1. Load the test Q&A dataset
    2. For each question, run the RAG pipeline
    3. Collect (question, answer, contexts, ground_truth) tuples
    4. Evaluate using Ragas metrics
    5. Print the results
    """
    from app.services.rag_graph import rag_graph

    # Import Ragas
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset
    except ImportError:
        print("Please install ragas: pip install ragas datasets")
        return

    dataset = load_test_dataset()
    print(f"Loaded {len(dataset)} test samples\n")

    # Collect results
    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for i, sample in enumerate(dataset):
        print(f"Processing {i+1}/{len(dataset)}: {sample['question'][:60]}...")

        # Run the RAG pipeline
        result = rag_graph.invoke({
            "question": sample["question"],
            "standalone_query": "",
            "chat_history": [],
            "video_id": sample.get("video_id"),
            "documents": [],
            "answer": "",
            "sources": [],
            "retry_count": 0,
        })

        questions.append(sample["question"])
        answers.append(result["answer"])
        contexts.append([
            doc.page_content for doc in result.get("documents", [])
        ])
        ground_truths.append(sample["ground_truth"])

    # Create Ragas dataset
    eval_dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    # Run evaluation
    print("\nRunning Ragas evaluation...")
    results = evaluate(
        eval_dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
    )

    # Print results
    print("\n" + "=" * 60)
    print("RAG EVALUATION RESULTS")
    print("=" * 60)

    for metric, score in results.items():
        print(f"  {metric:25s}: {score:.4f}")

    print("=" * 60)

    return results


if __name__ == "__main__":
    run_evaluation()

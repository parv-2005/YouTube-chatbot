# YouTube Intelligence Platform

An industrial-level AI chatbot that lets you **chat with any YouTube video** using RAG (Retrieval-Augmented Generation), LangGraph agentic workflows, and Google Gemini.

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────┐    ┌───────┐
│  Next.js UI  │───▶│  FastAPI    │───▶│ Qdrant  │    │ Redis │
│  (React 19)  │    │  Backend    │    │ Vector  │    │ Cache │
└─────────────┘    │             │    │ Store   │    └───────┘
                   │  LangGraph  │    └─────────┘
                   │  RAG Graph  │
                   │             │───▶ PostgreSQL
                   │  Gemini LLM │    (Users, Conversations)
                   └─────────────┘
```

## Key Features

- **Hybrid RAG Pipeline**: Vector search (Qdrant) + BM25 keyword search, fused with Reciprocal Rank Fusion
- **Cross-Encoder Reranking**: ms-marco-MiniLM re-scores candidates for precision
- **LangGraph Agentic Workflow**: Conditional routing with query rewriting and relevance checking
- **Whisper Fallback**: Local speech-to-text for videos without YouTube transcripts
- **Streaming Responses**: Server-Sent Events (SSE) for real-time token-by-token answers
- **Timestamped Sources**: Every answer cites the exact video timestamp
- **JWT Authentication**: Secure user system with bcrypt password hashing
- **Redis Caching**: Query result caching and sliding-window rate limiting
- **Ragas Evaluation**: Built-in RAG quality metrics (faithfulness, relevancy, precision, recall)

## Tech Stack

| Layer       | Technology                         |
|-------------|-------------------------------------|
| Frontend    | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend     | FastAPI, Python 3.11               |
| AI/LLM      | Google Gemini, LangChain, LangGraph |
| Embeddings  | Gemini Embedding 001               |
| Vector DB   | Qdrant                             |
| Keyword     | BM25 (rank-bm25)                   |
| Reranker    | Cross-Encoder (sentence-transformers) |
| Database    | PostgreSQL (SQLAlchemy)             |
| Cache       | Redis                              |
| Transcripts | YouTube Transcript API + Whisper   |
| Audio       | yt-dlp + FFmpeg                    |
| Auth        | JWT + bcrypt                       |
| Evaluation  | Ragas                              |

## RAG Pipeline Flow

```
User Question
     │
     ▼
Query Analysis ──────── Rewrites follow-up questions using chat history
     │
     ▼
Hybrid Search ──────── Vector (semantic) + BM25 (keyword) + RRF fusion
     │                 → Top 20 candidates
     ▼
Reranker ───────────── Cross-encoder re-scores for precision
     │                 → Top 5 chunks
     ▼
Relevance Check ────── Are chunks good enough?
     │
     ├── YES → Answer Generation (Gemini) → Response with sources
     │
     └── NO  → Rewrite Query → Retry retrieval (max 2 retries)
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16
- Redis 7
- Qdrant
- FFmpeg (for Whisper)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Copy environment
cp .env.local.example .env.local

# Run
npm run dev
```

### Docker (all services)

```bash
docker-compose up -d
```

## Project Structure

```
youtube-chatbot/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── core/          # Config, security, logging, dependencies
│   │   ├── database/      # SQLAlchemy models and session
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # Business logic layer
│   │   │   ├── rag_graph.py         # LangGraph workflow (the brain)
│   │   │   ├── retrieval_service.py # Hybrid search + RRF
│   │   │   ├── reranker_service.py  # Cross-encoder reranking
│   │   │   ├── llm_service.py       # Gemini + LangChain
│   │   │   ├── vector_store.py      # Qdrant operations
│   │   │   ├── bm25_service.py      # Keyword search
│   │   │   └── ...                  # Transcript, chunking, etc.
│   │   ├── utils/         # Helper utilities
│   │   └── main.py        # FastAPI app entry point
│   ├── evaluation/        # Ragas evaluation scripts
│   └── tests/             # Unit tests
├── frontend/
│   └── src/
│       ├── app/           # Next.js pages (landing, dashboard, chat)
│       ├── lib/           # API client, auth, utilities
│       └── types/         # TypeScript type definitions
├── docker-compose.yml
└── README.md
```

## API Endpoints

| Method | Endpoint                | Description                      |
|--------|-------------------------|----------------------------------|
| POST   | `/api/auth/register`    | Register a new user              |
| POST   | `/api/auth/login`       | Login and get JWT token          |
| GET    | `/api/auth/me`          | Get current user profile         |
| POST   | `/api/videos/ingest`    | Ingest a YouTube video           |
| GET    | `/api/videos`           | List all ingested videos         |
| POST   | `/api/conversations`    | Create a new conversation        |
| GET    | `/api/conversations`    | List user's conversations        |
| POST   | `/api/chat`             | Send a message (full response)   |
| POST   | `/api/chat/stream`      | Send a message (SSE streaming)   |
| GET    | `/api/health`           | Health check                     |

## Evaluation

```bash
cd backend
python -m evaluation.evaluate
```

Metrics measured:
- **Faithfulness**: Is the answer grounded in the context?
- **Answer Relevancy**: Does the answer address the question?
- **Context Precision**: Are retrieved chunks relevant?
- **Context Recall**: Was all relevant information retrieved?

## License

MIT

# LangC Advanced RAG API

A deployable advanced Retrieval-Augmented Generation API built with FastAPI, LangChain, OpenAI, Chroma, LangSmith, and optional Supabase integration.

This repo is cleaned up as a portfolio-ready project: one production API, organized source code, preserved learning examples, deployment config, and clear setup steps.

## What It Does

- Answers questions through a FastAPI `/ask` endpoint.
- Uses OpenAI embeddings and Chroma vector search.
- Supports multiple advanced RAG retrieval modes.
- Adds source/topic context to chunks before embedding.
- Returns answers with source names and retrieval metadata.
- Uses LangSmith tracing when enabled.
- Includes optional Supabase health validation for future persistence.

## Advanced RAG Modes

```text
basic        Vector similarity retrieval
multi_query  Generates multiple search queries to improve recall
hybrid       Combines vector retrieval with keyword retrieval
agentic      Checks retrieval quality, rewrites weak queries, and retries
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What advanced RAG features are included?","mode":"agentic"}'
```

## Project Structure

```text
LangC/
├── app.py
├── requirements.txt
├── pyproject.toml
├── render.yaml
├── README.md
├── .env.example
├── src/
│   ├── config.py
│   ├── schemas.py
│   └── rag/
│       ├── documents.py
│       ├── engine.py
│       └── prompts.py
├── examples/
│   ├── advanced_rag/
│   ├── basic_langchain/
│   └── langgraph/
└── tests/
    └── test_health.py
```

## Important Files

```text
app.py                  FastAPI routes and deploy entrypoint
src/config.py           Environment and model configuration
src/schemas.py          Request/response models
src/rag/engine.py       Advanced RAG engine
src/rag/prompts.py      Prompt templates
src/rag/documents.py    Current knowledge base
examples/               Preserved course and advanced RAG demos
render.yaml             Render free-tier deployment config
```

## Local Setup

Use Python 3.12. The project intentionally avoids Python 3.14 because some AI
packages can be slow or unstable there.

Install dependencies with pip:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Or with `uv` after regenerating the lock for Python 3.12:

```bash
uv lock --python 3.12
uv sync
```

Run locally:

```bash
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

```text
GET  /                 API info
GET  /health           Health check
GET  /features         Lists RAG capabilities
POST /ask              Ask a RAG question
GET  /supabase/health  Checks Supabase config
```

## Environment Variables

Create `.env` from `.env.example`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=multi-agent-research

SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

Supabase is optional for the current API. The app runs without it, but `/supabase/health` will return `configured: false`.

## LangSmith Setup

1. Create a LangSmith API key.
2. Add `LANGSMITH_API_KEY` to `.env`.
3. Set `LANGSMITH_TRACING=true`.
4. Set `LANGSMITH_PROJECT=multi-agent-research`.
5. Run the API and call `/ask`.
6. Check LangSmith for traces under that project.

LangSmith projects usually appear after the first traced request.

## Supabase Setup

1. Create a free Supabase project.
2. Copy the project URL.
3. Copy the anon/public key.
4. Add both to `.env`.
5. Run the API.
6. Visit `/supabase/health`.

Use Supabase later for uploaded documents, metadata, chat history, user auth, or persistent vector metadata.

## Deployment Plan

Recommended free-tier deployment:

```text
Hosting: Render
LLM: OpenAI
Tracing: LangSmith
Optional DB: Supabase
```

Render settings:

```text
Build command: pip install -r requirements.txt
Start command: uvicorn app:app --host 0.0.0.0 --port $PORT
Health check: /health
```

Add these Render environment variables:

```text
OPENAI_API_KEY
OPENAI_CHAT_MODEL
OPENAI_EMBEDDING_MODEL
LANGSMITH_TRACING
LANGSMITH_API_KEY
LANGSMITH_PROJECT
SUPABASE_URL
SUPABASE_KEY
```

## Testing

```bash
.venv/bin/python -m unittest discover -s tests
```

The current tests validate health and feature metadata without calling OpenAI.

## Resume Bullet

Built a production-style advanced RAG API using FastAPI, LangChain, OpenAI embeddings, Chroma vector search, contextual chunking, multi-query retrieval, hybrid keyword/vector retrieval, and agentic query rewrite/retry, with LangSmith observability, optional Supabase integration, tests, and Render-ready deployment configuration.

## Next Production Improvements

- Add document upload and ingestion endpoints.
- Persist uploaded document metadata in Supabase.
- Add authentication before public deployment.
- Add evaluation datasets in LangSmith.
- Add rate limiting and request logging.
- Replace local Chroma with a managed vector database if traffic grows.

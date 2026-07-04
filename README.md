# LangC Advanced RAG API

A deployable advanced Retrieval-Augmented Generation API built with FastAPI, LangChain, OpenAI, Chroma, LangSmith, and optional Supabase integration.

This repo is cleaned up as a portfolio-ready project: one production API, organized source code, preserved learning examples, deployment config, and clear setup steps.

## What It Does

- Answers questions through a FastAPI `/ask` endpoint.
- Uploads documents, ingests them, and answers questions grounded in them
  through `/documents/*` and `/query/documents`.
- Uses OpenAI embeddings and Chroma vector search for both flows.
- Supports multiple advanced RAG retrieval modes on `/ask`.
- Adds source/topic context to chunks before embedding.
- Returns answers with source names and retrieval metadata.
- Protects document and query routes with an `X-API-Key` header.
- Rate limits the answer endpoints per client IP.
- Persists document metadata in Supabase when configured, with a local JSON
  fallback.
- Ships a minimal static web UI (`frontend/`) for upload, listing, and querying.
- Restricts browser access with an explicit CORS allow-list.
- Uses LangSmith tracing when enabled.

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
├── requirements.txt
├── pyproject.toml
├── render.yaml
├── README.md
├── .env.example
├── app/
│   ├── main.py                    FastAPI app, CORS, rate limiter
│   ├── core/
│   │   ├── config.py              Env + model configuration
│   │   ├── rate_limit.py          slowapi limiter
│   │   └── offline.py             Force local/no-network backends
│   ├── api/
│   │   ├── dependencies.py        RAG engine + X-API-Key auth
│   │   ├── routes_health.py       /, /health, /features, /supabase/health
│   │   ├── routes_query.py        /ask, /query/documents
│   │   └── routes_documents.py    /documents upload/list/ingest/chunks
│   ├── services/
│   │   ├── rag_service.py         Advanced RAG engine (/ask)
│   │   ├── rag_backends.py        OpenAI vs local embedding/LLM selection
│   │   ├── local_embeddings.py    Deterministic offline embeddings
│   │   ├── vector_store.py        Chroma collection for uploaded docs
│   │   ├── document_service.py    Upload + metadata (Supabase/local)
│   │   ├── document_qa_service.py Grounded QA over uploaded docs
│   │   ├── chunk_service.py       Chunking + ingest
│   │   ├── rag_documents.py       Built-in knowledge base (/ask)
│   │   └── rag_prompts.py         Prompt templates
│   ├── schemas/                   Request/response models
│   └── db/
│       ├── supabase_client.py     Supabase client helper
│       └── document_repository.py Supabase documents table access
├── frontend/
│   ├── index.html                 Static web UI
│   └── e2e/                       Headless Playwright test
├── supabase/
│   └── migrations/                SQL schema (documents table)
├── evals/                         Local RAG evaluation pipeline
├── examples/                      Preserved course and advanced RAG demos
└── tests/                         Unit + integration tests
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
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Makefile Commands

Common tasks are wrapped in a `Makefile`. Override the interpreter with
`PYTHON=` (for example `make test PYTHON=.venv/bin/python`).

```text
make install       Install dependencies from requirements.txt
make test          Run the test suite
make run           Run the API locally on port 8000
make eval          Run the local RAG evaluation
make docker-build  Build the Docker image
make docker-run    Run the Docker image (uses .env if present)
```

## Docker

Build and run with Docker:

```bash
make docker-build
make docker-run
```

Or directly:

```bash
docker build -t docuintelai .
docker run -p 8000:8000 docuintelai
```

The API boots without any credentials. To supply them, create `.env` from
`.env.example`; `docker run` and `docker compose` pick it up automatically when
present and start fine without it.

With Docker Compose (persists uploaded documents in `./storage`):

```bash
docker compose up --build
```

## Frontend (Web UI)

A single static page (`frontend/index.html`, plain HTML/CSS/JS, no build step)
provides upload, document listing, and grounded querying with sources and a
confidence score. It calls `/features` on connect and shows the active
embedding backend (`openai` or `local_hash`).

Run the backend with an API key configured, then serve the folder statically:

```bash
API_KEY=demo-key .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m http.server 5500 --directory frontend
# open http://127.0.0.1:5500
```

In the UI set the API base URL and API key, click **Save & connect**, upload a
document, then ask a question. The API key is stored in `localStorage` and sent
as `X-API-Key` — a **demo-only** convenience, not secure credential storage.

An automated headless-browser test lives in `frontend/e2e/` and drives the
three actions end-to-end:

```bash
BACKEND_MODE=local bash frontend/e2e/run.sh   # boots backend + static, runs the test
```

## CORS

Browser access is restricted to an explicit allow-list (not `*`). It defaults
to the local static frontend origins and is configurable via
`CORS_ALLOW_ORIGINS` (comma-separated):

```text
CORS_ALLOW_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
```

Requests from any other origin are rejected by the browser preflight.

## API Endpoints

```text
GET  /                          API info
GET  /health                    Health check
GET  /features                  Lists RAG capabilities
POST /ask                       Ask a RAG question (rate limited)
GET  /supabase/health           Checks Supabase config
POST /documents/upload          Upload a .txt/.md/.pdf document (auth)
GET  /documents                 List uploaded documents (auth)
POST /documents/{id}/ingest     Chunk + embed a document into Chroma (auth)
GET  /documents/{id}/chunks     List a document's chunks (auth)
POST /query/documents           Answer from uploaded docs (auth, rate limited)
```

Routes marked `(auth)` require the `X-API-Key` header when `API_KEY` is set;
`/health` and `/features` are always open.

## Authentication

Set `API_KEY` in the environment to require an `X-API-Key` header on all
`/documents/*` and `/query/*` routes:

```bash
curl -X POST http://127.0.0.1:8000/query/documents \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"What does the uploaded document say?"}'
```

Auth **fails closed**: if `API_KEY` is unset or empty, every `/documents/*` and
`/query/*` request is rejected with 401 (the routes are locked, never silently
open). The app still boots without credentials — the protected routes are just
unusable until `API_KEY` is configured. `/health` and `/features` remain open.

## Rate Limiting

`/ask` and `/query/documents` are rate limited per client IP via slowapi.
Configure the limit with `RATE_LIMIT` (slowapi syntax, default `30/minute`).
Exceeding it returns HTTP 429.

## Uploaded-Document RAG

`/query/documents` answers strictly from uploaded documents:

1. `POST /documents/upload` stores a `.txt`, `.md`, or `.pdf` file.
2. `POST /documents/{id}/ingest` chunks the text and embeds the chunks into a
   Chroma collection.
3. `POST /query/documents` embeds the question, retrieves the most similar
   chunks, and generates a grounded answer from them.

When `OPENAI_API_KEY` is set, this flow uses OpenAI embeddings and an OpenAI
chat model. Without a key it falls back to a deterministic local embedding and
an extractive answer built from the retrieved chunks, so it runs fully offline.
This fallback has lower retrieval quality, so it is never silent: the app logs
a warning and `/features` reports the active backend as
`"embedding_backend": "local_hash"` (vs `"openai"`). Chunks scoring below
`RAG_RELEVANCE_THRESHOLD` are ignored; if none qualify the endpoint returns a
fallback message with no sources.

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
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_KEY=your_supabase_anon_key

API_KEY=your_api_key
RATE_LIMIT=30/minute
CORS_ALLOW_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
```

See `.env.example` for the full list. Supabase is optional; the app runs
without it, and `/supabase/health` will return `configured: false`.

## LangSmith Setup

1. Create a LangSmith API key.
2. Add `LANGSMITH_API_KEY` to `.env`.
3. Set `LANGSMITH_TRACING=true`.
4. Set `LANGSMITH_PROJECT=multi-agent-research`.
5. Run the API and call `/ask`.
6. Check LangSmith for traces under that project.

LangSmith projects usually appear after the first traced request.

## Supabase Setup

When `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set, document metadata
(the `DocumentMetadata` fields) is persisted to a Supabase `documents` table
instead of the local `storage/documents.json` file. When they are unset, the
app falls back to local JSON.

**Key model (security-relevant):** the backend talks to Supabase exclusively
with the **service-role key** (`SUPABASE_SERVICE_ROLE_KEY`), which bypasses RLS
by design and must live server-side only — never in the frontend, never in
logs. The **anon/publishable key** (`SUPABASE_KEY`) has zero access to the
`documents` table: RLS is enabled with no policies for `anon`/`authenticated`
(see `supabase/migrations/002_lock_down_documents_rls.sql`), so holding the
anon key does not let anyone bypass the FastAPI auth layer. The frontend never
talks to Supabase at all; it only calls this API.

1. Create a free Supabase project.
2. Copy the project URL and the **service-role** key into `.env`
   (`SUPABASE_SERVICE_ROLE_KEY`).
3. Provision the schema from this repo — do not create the table by hand:

   ```bash
   supabase link --project-ref <your-project-ref>
   supabase db push        # applies supabase/migrations/*.sql
   ```

   The migrations create `public.documents` with columns matching
   `app/schemas/document.py` exactly (`document_id`, `filename`, `file_type`,
   `status`, `created_at`), enable RLS, and leave no anon policies.
4. Run the API and visit `/supabase/health` (reports which key type is
   configured).

The `documents` table must exist before uploads work with Supabase enabled —
`tests/test_supabase_integration.py` exercises this end-to-end against a real
project (and is skipped when no credentials are present).

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
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
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
SUPABASE_SERVICE_ROLE_KEY
API_KEY
RATE_LIMIT
CORS_ALLOW_ORIGINS
```

## Testing

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

The tests cover health/feature metadata, document upload and ingestion, the
uploaded-document RAG flow (embedding retrieval via Chroma), API-key auth, and
rate limiting. They run fully offline by default: the suite forces the local
embedding backend, so no OpenAI calls are made.

`tests/test_supabase_integration.py` is an integration test that runs against a
real Supabase project. It is skipped unless credentials are provided, and runs
in CI via the `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` GitHub Actions
secrets (passed as `SUPABASE_TEST_URL` / `SUPABASE_TEST_KEY`). A separate CI job runs the
Playwright frontend end-to-end test. See `.github/workflows/tests.yml`.

## Evaluations

A local evaluation pipeline measures the quality of the uploaded-document RAG
flow. It seeds a fixed corpus into an isolated temporary storage directory,
runs the questions in `evals/questions.json` through the same
`/query/documents` retrieval pipeline (Chroma similarity search), and writes a
report to `evals/results.md`.

It uses the same retrieval backend as `/query/documents`: OpenAI embeddings
when `OPENAI_API_KEY` is set, otherwise the offline local embedding backend
(no network calls). The test suite always runs it against the local backend.

Run the evals:

```bash
.venv/bin/python -m evals.run_eval
```

Reported metrics:

```text
retrieval hit rate         expected document appears in the returned sources
citation/source presence   answerable questions return non-empty sources
fallback accuracy          out-of-scope questions return the fallback message
latency_ms                 per-question and average answer latency
```

Edit `evals/questions.json` to add cases. Each item has a `type` of
`answerable` (with `expected_source` and `expected_keywords`) or `fallback`.

## Resume Bullet

Built a production-style advanced RAG API using FastAPI, LangChain, OpenAI embeddings, Chroma vector search, contextual chunking, multi-query retrieval, hybrid keyword/vector retrieval, and agentic query rewrite/retry, with LangSmith observability, optional Supabase integration, tests, and Render-ready deployment configuration.

## Still Missing / Future Work

The following are genuinely not yet done after this phase:

- Request logging and structured observability for the document routes.
- Per-key (not just per-IP) rate limiting and multiple API keys / roles.
- Storing uploaded files and Chroma vectors in durable cloud storage rather
  than the local `storage/` directory (metadata already persists to Supabase
  when configured).
- Evaluation datasets in LangSmith (the local eval in `evals/` is offline).
- A managed vector database if traffic outgrows local Chroma.

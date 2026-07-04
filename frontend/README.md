# DocuIntelAI Frontend

A single static `index.html` (plain HTML/CSS/JS, no build step) for the FastAPI
backend. It covers document upload (with automatic ingest), the document list,
and grounded querying with sources and confidence score.

## Run

Start the backend (with an API key configured):

```bash
API_KEY=demo-key .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Serve this folder as static files (any static server works):

```bash
python -m http.server 5500 --directory frontend
# open http://127.0.0.1:5500
```

In the UI, set **API base URL** (e.g. `http://127.0.0.1:8000`) and **API key**,
click *Save & connect*, then upload a document and ask a question.

Because the page is served from a different origin than the API, it relies on
the backend's existing permissive CORS config — no backend changes were made.

## Security note

The API key is stored in `localStorage` and sent as `X-API-Key`. This is a
**demo-only** convenience, not secure production credential storage.

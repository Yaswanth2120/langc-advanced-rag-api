# Phase 7: Minimal Frontend

Goal:
Give DocuIntelAI a usable UI instead of relying on Swagger /docs.

Requirements:
- Upload form: POST /documents/upload
- Document list view: GET /documents
- Query interface: POST /query/documents, display answer, sources,
  confidence_score
- API key input field, sent as X-API-Key header on every request
- Basic error display for 401/429/500 responses

Constraints:
- Do not modify backend routes/schemas unless required; state why if so.
- No new backend dependencies.
- Keep it deployable as static files or a single lightweight server.

Stop after Phase 7 is complete.
# Phase 6: Merge RAG Pipelines + Production Hardening

Goal:
Replace the BM25 keyword retrieval in /query/documents with the
existing embeddings + Chroma engine, and close the gaps that block
deployment: auth, rate limiting, dead Supabase integration, stale docs.

Requirements:

Retrieval merge:
- Embed uploaded document chunks into a Chroma collection at ingest
  time (POST /documents/{id}/ingest), using AdvancedRAGEngine's
  existing embedding config.
- /query/documents retrieves via Chroma similarity search, not BM25.
- /query/documents generates the answer with the LLM from retrieved
  chunks, not raw concatenation.
- Delete app/services/document_qa_service.py's BM25 code path once
  replaced. One retrieval path only.

Auth:
- Require header X-API-Key on all /documents/* and /query/* routes.
- Validate against env var API_KEY.
- /health and /features stay open.
- Add API_KEY to .env.example and app/core/config.py.

Rate limiting:
- Add slowapi.
- Limit /ask and /query/documents per IP, configurable via env var.

Supabase:
- app/db/supabase_client.py is unused by document_service.py today.
- Wire it: persist document metadata in Supabase when
  SUPABASE_URL/SUPABASE_KEY are set, fall back to local JSON when not.
- Do not leave it unused.

Tests:
- Update tests/test_rag_pipeline.py for embedding-based retrieval;
  remove BM25 assertions.
- Add auth tests: 401 without key, 200 with valid key.
- Add rate-limit test.
- Full suite must pass before this phase is marked done.

README:
- Remove the stale "Next Production Improvements" section.
- Replace with whatever is still missing after this phase, accurately.

Constraints:
- Do not modify /ask's existing behavior or config.
- Do not touch phase 1-5 code outside what's listed above.
- Ask before deleting files you didn't create this phase.

Stop after Phase 6 is complete and tests pass.
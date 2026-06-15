# Phase 4: RAG Evaluation System

Goal:
Add an evaluation pipeline to measure DocuIntelAI answer quality.

Requirements:
- Create evals/questions.json
- Create evals/run_eval.py
- Create evals/results.md
- Evaluate:
  - retrieval hit rate
  - citation/source presence
  - fallback accuracy
  - latency_ms
- Use local uploaded-document pipeline only.
- No OpenAI calls.
- No embeddings.
- No vector database.
- Add tests for eval runner if practical.
- Update README with how to run evals.

Constraints:
- Do not modify /ask behavior.
- Do not change document upload behavior.
- Do not add external services.
- Do not delete files.

Stop after Phase 4 is complete.
# Phase 1: Project Refactor

Goal:
Transform the current FastAPI RAG API into a production-ready structure.

Requirements:

Move code into:

app/
  main.py
  core/
    config.py
  api/
    routes_health.py
    routes_query.py
  services/
    rag_service.py
  schemas/
  db/

Preserve existing functionality.

Keep endpoints working:

- /health
- /features
- query endpoint

Move business logic out of app.py.

Update imports.

Update tests.

Run pytest and fix failures.

Do not implement new features.

Stop after refactoring is complete.
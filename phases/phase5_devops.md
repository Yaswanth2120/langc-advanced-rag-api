# Phase 5: DevOps and Production Readiness

Goal:
Make DocuIntelAI easy to run, test, and deploy.

Requirements:
- Add Dockerfile
- Add docker-compose.yml
- Add .env.example
- Add GitHub Actions workflow for tests
- Add Makefile with commands:
  - install
  - test
  - run
  - eval
  - docker-build
  - docker-run
- Update README with:
  - local setup
  - test command
  - eval command
  - Docker run command
  - environment variables

Constraints:
- Do not modify app logic.
- Do not modify /ask.
- Do not modify document upload/query/eval behavior.
- Do not add embeddings.
- Do not add vector database.
- Do not add external services.
- Do not delete files.

Stop after Phase 5 is complete.
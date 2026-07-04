#!/usr/bin/env bash
# Boot the backend + static frontend, run the headless E2E test, tear down.
#
# Env:
#   BACKEND_MODE = local (default) | openai   -- which embedding backend to use
#   API_KEY      = demo-key (default)
#   PYTHON       = python interpreter (default: ../../.venv/bin/python)
#
# Exit code is the test's exit code.
set -u
cd "$(dirname "$0")"
REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
API_KEY="${API_KEY:-demo-key}"
BACKEND_MODE="${BACKEND_MODE:-local}"

# In local mode, force the offline embedding backend (empty OpenAI key). In
# openai mode, leave OPENAI_API_KEY alone so config loads it from .env.
# (Avoid bash arrays here: macOS ships bash 3.2, where expanding an empty array
# under `set -u` errors.)
if [ "$BACKEND_MODE" = "local" ]; then export OPENAI_API_KEY=""; fi

echo "== starting backend ($BACKEND_MODE) and static server =="
( cd "$REPO_ROOT" && API_KEY="$API_KEY" \
  "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning ) &
BACK=$!
( cd "$REPO_ROOT" && "$PYTHON" -m http.server 5500 --directory frontend ) &
STATIC=$!

cleanup() { kill "$BACK" "$STATIC" 2>/dev/null; }
trap cleanup EXIT

for i in $(seq 1 30); do
  curl -sf -o /dev/null http://127.0.0.1:8000/health && curl -sf -o /dev/null http://127.0.0.1:5500/index.html && break
  sleep 1
done

echo "== running frontend E2E test =="
API_KEY="$API_KEY" node frontend.test.js
CODE=$?
echo "== e2e exit code: $CODE =="
exit $CODE

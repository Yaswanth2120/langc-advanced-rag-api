"""Test package bootstrap.

Forces the suite to run fully offline and deterministically regardless of any
local ``.env``: no OpenAI (local embeddings + extractive answers), no Supabase
(local JSON metadata). A fixed ``API_KEY`` is configured so auth is enabled
(fail-closed) and the tests can authenticate with it.

External credentials are set to empty strings rather than unset because
``python-dotenv`` (called in ``app.core.config``) does not override variables
already present in the environment. This module is imported before any test
module, so it runs before ``app.core.config`` reads the environment.
"""

import os

# The key the suite authenticates with. Kept in sync with the inline guards at
# the top of the test modules (used when the suite is run without importing the
# tests package first).
TEST_API_KEY = "test-api-key"

for _var in (
    "OPENAI_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "LANGSMITH_API_KEY",
):
    os.environ[_var] = ""

os.environ["API_KEY"] = TEST_API_KEY
os.environ["LANGSMITH_TRACING"] = "false"

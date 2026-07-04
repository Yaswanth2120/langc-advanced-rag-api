import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Force offline/deterministic config before app import (mirrors tests/__init__,
# in case the suite is run without the tests package being imported first).
for _var in ("OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "LANGSMITH_API_KEY"):
    os.environ[_var] = ""
os.environ["API_KEY"] = "test-api-key"
os.environ["LANGSMITH_TRACING"] = "false"

from fastapi.testclient import TestClient

from app.api.dependencies import get_rag_engine
from app.core import rate_limit
from app.main import app
from app.services import document_service, vector_store


API_KEY = "test-api-key"


class RateLimitTestCase(unittest.TestCase):
    """Per-IP rate limiting on /query/documents."""

    def setUp(self):
        self.client = TestClient(app, headers={"X-API-Key": API_KEY})
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._original_storage = document_service.STORAGE_DIR
        document_service.configure_storage(self._tmp_dir)
        vector_store.reset()
        get_rag_engine.cache_clear()
        # Isolate slowapi's per-IP counters: start from a clean slate and set a
        # low limit local to this test, restoring both on teardown.
        self._original_limit = rate_limit.current_rate_limit()
        rate_limit.set_rate_limit("2/minute")
        rate_limit.reset_limits()

    def tearDown(self):
        rate_limit.set_rate_limit(self._original_limit)
        rate_limit.reset_limits()
        vector_store.reset()
        get_rag_engine.cache_clear()
        document_service.configure_storage(self._original_storage)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_requests_over_limit_are_throttled(self):
        payload = {"question": "anything"}

        # First two requests are within the 2/minute limit.
        self.assertEqual(
            self.client.post("/query/documents", json=payload).status_code, 200
        )
        self.assertEqual(
            self.client.post("/query/documents", json=payload).status_code, 200
        )

        # The third request from the same IP is throttled.
        self.assertEqual(
            self.client.post("/query/documents", json=payload).status_code, 429
        )


if __name__ == "__main__":
    unittest.main()

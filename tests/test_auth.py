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

from app.api.dependencies import expected_api_key, get_rag_engine
from app.main import app
from app.services import document_service, vector_store


API_KEY = "test-api-key"

# The routes that must be protected by X-API-Key.
PROTECTED = [
    ("GET", "/documents"),
    ("POST", "/documents/upload"),
    ("POST", "/query/documents"),
]


def _call(client: TestClient, method: str, path: str, headers=None):
    if method == "GET":
        return client.get(path, headers=headers)
    if path == "/documents/upload":
        return client.post(
            path,
            files={"file": ("n.txt", b"hi", "text/plain")},
            headers=headers,
        )
    return client.post(path, json={"question": "anything"}, headers=headers)


class AuthConfiguredTestCase(unittest.TestCase):
    """API_KEY is configured: correct key allowed, missing/wrong key rejected."""

    def setUp(self):
        self.client = TestClient(app)
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._original_storage = document_service.STORAGE_DIR
        document_service.configure_storage(self._tmp_dir)
        vector_store.reset()
        get_rag_engine.cache_clear()
        app.dependency_overrides[expected_api_key] = lambda: API_KEY

    def tearDown(self):
        app.dependency_overrides.pop(expected_api_key, None)
        vector_store.reset()
        get_rag_engine.cache_clear()
        document_service.configure_storage(self._original_storage)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_missing_key_rejected(self):
        for method, path in PROTECTED:
            with self.subTest(route=f"{method} {path}"):
                self.assertEqual(_call(self.client, method, path).status_code, 401)

    def test_wrong_key_rejected(self):
        headers = {"X-API-Key": "wrong"}
        for method, path in PROTECTED:
            with self.subTest(route=f"{method} {path}"):
                self.assertEqual(
                    _call(self.client, method, path, headers).status_code, 401
                )

    def test_valid_key_allowed(self):
        headers = {"X-API-Key": API_KEY}
        response = self.client.get("/documents", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_query_valid_key_allowed(self):
        headers = {"X-API-Key": API_KEY}
        response = self.client.post(
            "/query/documents", json={"question": "anything"}, headers=headers
        )
        self.assertEqual(response.status_code, 200)


class AuthUnsetKeyFailsClosedTestCase(unittest.TestCase):
    """API_KEY unset/empty: every protected route is rejected (fail closed)."""

    def setUp(self):
        self.client = TestClient(app)
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._original_storage = document_service.STORAGE_DIR
        document_service.configure_storage(self._tmp_dir)
        vector_store.reset()
        get_rag_engine.cache_clear()
        # Simulate API_KEY being unset on the server.
        app.dependency_overrides[expected_api_key] = lambda: None

    def tearDown(self):
        app.dependency_overrides.pop(expected_api_key, None)
        vector_store.reset()
        get_rag_engine.cache_clear()
        document_service.configure_storage(self._original_storage)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_all_protected_routes_rejected_without_header(self):
        for method, path in PROTECTED:
            with self.subTest(route=f"{method} {path}"):
                self.assertEqual(_call(self.client, method, path).status_code, 401)

    def test_all_protected_routes_rejected_even_with_a_header(self):
        # Fail closed: with no server key, no client-supplied key can pass.
        headers = {"X-API-Key": "anything-at-all"}
        for method, path in PROTECTED:
            with self.subTest(route=f"{method} {path}"):
                self.assertEqual(
                    _call(self.client, method, path, headers).status_code, 401
                )


class AuthOpenRoutesTestCase(unittest.TestCase):
    """/health and /features are never protected."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_and_features_stay_open(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/features").status_code, 200)


if __name__ == "__main__":
    unittest.main()

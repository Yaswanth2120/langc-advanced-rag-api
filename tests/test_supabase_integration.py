"""Integration test for the Supabase-backed document metadata path.

Unlike the rest of the suite, this test does NOT run offline. It forces
``offline=False`` and points the app at a real Supabase project, then drives
the HTTP layer: it uploads a document (``document_repository.insert``) and
lists documents (``document_repository.list_all``) through the FastAPI app.

Key selection (server-side key, fed through the service-role slot):
1. ``SUPABASE_TEST_KEY`` env var (CI maps the SUPABASE_SERVICE_ROLE_KEY
   secret here),
2. ``SUPABASE_SERVICE_ROLE_KEY`` from ``.env``,
3. ``SUPABASE_KEY`` (anon) from ``.env`` — works ONLY until RLS lockdown
   (supabase/migrations/002) is applied; after that this test will fail with
   anon credentials, which is the desired signal to switch to service-role.

The Supabase code path is exercised for real (``enabled() is True``), not
skipped or stubbed out. It fails when the ``documents`` table has not been
provisioned from ``supabase/migrations/``. It is skipped only when no
credentials are available at all (e.g. CI without secrets).
"""

import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV = dotenv_values(REPO_ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_TEST_URL") or _ENV.get("SUPABASE_URL")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_TEST_KEY")
    or _ENV.get("SUPABASE_SERVICE_ROLE_KEY")
    or _ENV.get("SUPABASE_KEY")
)

# Auth must be configured for the protected routes (fail-closed).
os.environ["API_KEY"] = os.environ.get("API_KEY") or "test-api-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.core import offline  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db import document_repository  # noqa: E402
from app.main import app  # noqa: E402
from app.services import document_service  # noqa: E402

API_KEY = os.environ["API_KEY"]


@unittest.skipUnless(
    SUPABASE_URL and SUPABASE_KEY,
    "SUPABASE_URL/SUPABASE_KEY not configured; real Supabase integration test skipped",
)
class SupabaseDocumentsIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, headers={"X-API-Key": API_KEY})
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._orig_storage = document_service.STORAGE_DIR
        document_service.configure_storage(self._tmp_dir)

        # Point the app at the real Supabase project with offline mode OFF.
        # The key goes into the service-role slot: that is the slot the
        # backend uses for table access (document_repository._backend_key).
        self._orig_offline = offline.is_offline()
        self._orig_url = settings.supabase_url
        self._orig_key = settings.supabase_key
        self._orig_service_key = settings.supabase_service_role_key
        offline.set_offline(False)
        object.__setattr__(settings, "supabase_url", SUPABASE_URL)
        object.__setattr__(settings, "supabase_service_role_key", SUPABASE_KEY)
        object.__setattr__(settings, "supabase_key", None)
        document_repository.reset_client()

        # Sanity: we are genuinely on the Supabase path, not local JSON.
        self.assertTrue(document_repository.enabled())

        self._created_ids: list[str] = []

    def tearDown(self):
        for document_id in self._created_ids:
            try:
                document_repository.delete(document_id)
            except Exception:
                pass
        object.__setattr__(settings, "supabase_url", self._orig_url)
        object.__setattr__(settings, "supabase_key", self._orig_key)
        object.__setattr__(settings, "supabase_service_role_key", self._orig_service_key)
        document_repository.reset_client()
        offline.set_offline(self._orig_offline)
        document_service.configure_storage(self._orig_storage)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_upload_then_list_roundtrips_through_supabase(self):
        marker = f"integ-{uuid.uuid4().hex[:8]}.txt"

        # Upload -> document_repository.insert() against the real table.
        upload = self.client.post(
            "/documents/upload",
            files={"file": (marker, b"supabase integration test body", "text/plain")},
        )
        self.assertEqual(upload.status_code, 200, upload.text)
        document_id = upload.json()["document_id"]
        self._created_ids.append(document_id)

        # List -> document_repository.list_all() against the real table.
        listed = self.client.get("/documents")
        self.assertEqual(listed.status_code, 200, listed.text)
        rows = listed.json()

        by_id = {row["document_id"]: row for row in rows}
        self.assertIn(document_id, by_id, "uploaded document not returned by Supabase list")
        # The row that came back from Supabase matches the schema field-for-field.
        row = by_id[document_id]
        self.assertEqual(row["filename"], marker)
        self.assertEqual(row["file_type"], "txt")
        self.assertEqual(row["status"], "uploaded")
        self.assertTrue(row["created_at"])


if __name__ == "__main__":
    unittest.main()

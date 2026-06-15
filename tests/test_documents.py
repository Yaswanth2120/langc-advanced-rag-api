import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import document_service


class DocumentsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._original_storage = document_service.STORAGE_DIR
        document_service.configure_storage(self._tmp_dir)

    def tearDown(self):
        document_service.configure_storage(self._original_storage)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_txt_upload_succeeds(self):
        response = self.client.post(
            "/documents/upload",
            files={"file": ("notes.txt", b"hello world", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["filename"], "notes.txt")
        self.assertEqual(body["file_type"], "txt")
        self.assertEqual(body["status"], "uploaded")
        self.assertTrue(body["document_id"])
        self.assertTrue(body["created_at"])

    def test_unsupported_file_type_rejected(self):
        response = self.client.post(
            "/documents/upload",
            files={"file": ("malware.exe", b"binary", "application/octet-stream")},
        )

        self.assertEqual(response.status_code, 400)

    def test_get_documents_returns_uploaded_metadata(self):
        self.client.post(
            "/documents/upload",
            files={"file": ("readme.md", b"# Title", "text/markdown")},
        )

        response = self.client.get("/documents")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["filename"], "readme.md")
        self.assertEqual(body[0]["file_type"], "md")


if __name__ == "__main__":
    unittest.main()

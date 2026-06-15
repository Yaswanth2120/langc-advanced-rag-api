import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import document_service
from app.services.document_qa_service import NO_CONTEXT_MESSAGE


class RAGPipelineTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._original_storage = document_service.STORAGE_DIR
        document_service.configure_storage(self._tmp_dir)

    def tearDown(self):
        document_service.configure_storage(self._original_storage)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _upload(self, filename: str, body: bytes) -> str:
        response = self.client.post(
            "/documents/upload",
            files={"file": (filename, body, "text/plain")},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["document_id"]

    def test_ingest_creates_chunks(self):
        doc_id = self._upload("notes.txt", b"Falcons are fast birds that hunt in open skies.")

        response = self.client.post(f"/documents/{doc_id}/ingest")

        self.assertEqual(response.status_code, 200)
        chunks = response.json()
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["document_id"], doc_id)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertTrue(chunks[0]["chunk_id"])
        self.assertTrue(chunks[0]["created_at"])

    def test_ingest_unknown_document_returns_404(self):
        response = self.client.post("/documents/does-not-exist/ingest")
        self.assertEqual(response.status_code, 404)

    def test_reingest_replaces_old_chunks(self):
        doc_id = self._upload("notes.txt", b"original content about turbines")
        self.client.post(f"/documents/{doc_id}/ingest")
        first = self.client.get(f"/documents/{doc_id}/chunks").json()

        # Re-ingesting the same document should not duplicate its chunks.
        self.client.post(f"/documents/{doc_id}/ingest")
        second = self.client.get(f"/documents/{doc_id}/chunks").json()

        self.assertEqual(len(first), len(second))
        self.assertNotEqual(first[0]["chunk_id"], second[0]["chunk_id"])

    def test_list_chunks(self):
        doc_id = self._upload("notes.txt", b"Photosynthesis converts sunlight into chemical energy.")
        self.client.post(f"/documents/{doc_id}/ingest")

        response = self.client.get(f"/documents/{doc_id}/chunks")

        self.assertEqual(response.status_code, 200)
        chunks = response.json()
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("Photosynthesis", chunks[0]["text"])

    def test_list_chunks_unknown_document_returns_404(self):
        response = self.client.get("/documents/missing/chunks")
        self.assertEqual(response.status_code, 404)

    def test_document_query_returns_grounded_answer(self):
        doc_id = self._upload(
            "space.txt",
            b"The Voyager spacecraft carries a golden record with sounds from Earth.",
        )
        self.client.post(f"/documents/{doc_id}/ingest")

        response = self.client.post(
            "/query/documents",
            json={"question": "What does the Voyager spacecraft carry?"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("golden record", body["answer"])
        self.assertEqual(body["sources"], [doc_id])
        self.assertGreater(body["confidence_score"], 0.0)

    def test_no_relevant_chunks_returns_fallback(self):
        doc_id = self._upload("space.txt", b"The Voyager spacecraft carries a golden record.")
        self.client.post(f"/documents/{doc_id}/ingest")

        response = self.client.post(
            "/query/documents",
            json={"question": "Explain quantum chromodynamics renormalization groups"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], NO_CONTEXT_MESSAGE)
        self.assertEqual(body["sources"], [])
        self.assertEqual(body["confidence_score"], 0.0)

    def test_query_with_no_documents_returns_fallback(self):
        response = self.client.post(
            "/query/documents",
            json={"question": "anything at all"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], NO_CONTEXT_MESSAGE)
        self.assertEqual(body["sources"], [])
        self.assertEqual(body["confidence_score"], 0.0)


if __name__ == "__main__":
    unittest.main()

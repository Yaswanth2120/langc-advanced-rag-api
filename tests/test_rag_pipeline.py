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
from app.services.document_qa_service import NO_CONTEXT_MESSAGE


API_KEY = "test-api-key"


class RAGPipelineTestCase(unittest.TestCase):
    """Exercises the ingest -> embed -> Chroma retrieval -> answer pipeline.

    Runs against the offline backend (deterministic local embeddings and an
    extractive answer built from the retrieved chunks), so no OpenAI calls are
    made. Retrieval always goes through the Chroma vector store.
    """

    def setUp(self):
        # Default the X-API-Key header on every request so protected routes pass.
        self.client = TestClient(app, headers={"X-API-Key": API_KEY})
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._original_storage = document_service.STORAGE_DIR
        document_service.configure_storage(self._tmp_dir)
        # Reset process-global state so tests do not leak into one another.
        vector_store.reset()
        get_rag_engine.cache_clear()
        rate_limit.reset_limits()

    def tearDown(self):
        vector_store.reset()
        get_rag_engine.cache_clear()
        rate_limit.reset_limits()
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

    def test_document_query_retrieves_via_embeddings(self):
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
        # Answer is grounded in the retrieved chunk.
        self.assertIn("golden record", body["answer"])
        # Similarity retrieval cites the source document.
        self.assertEqual(body["sources"], [doc_id])
        # Relevance-based confidence is populated for a real hit.
        self.assertGreater(body["confidence_score"], 0.0)

    def test_query_ignores_unrelated_document(self):
        # An off-topic document must not be retrieved: its similarity falls
        # below the relevance threshold, yielding the fallback response.
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

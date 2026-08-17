import json
import os
import unittest

for _var in ("OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "LANGSMITH_API_KEY"):
    os.environ[_var] = ""
os.environ["LANGSMITH_TRACING"] = "false"

from fastapi.testclient import TestClient

from app.api.dependencies import get_rag_engine
from app.core import rate_limit
from app.main import app


class AskPipelineTestCase(unittest.TestCase):
    """Exercises /ask end to end for all four retrieval modes.

    Runs against the offline backend (deterministic local hashing embeddings,
    no LLM), so no OpenAI calls are made. Before this test existed, the
    AdvancedRAGEngine had no offline path at all and this whole pipeline was
    untested outside of manual runs against a real OpenAI key.
    """

    def setUp(self):
        self.client = TestClient(app)
        get_rag_engine.cache_clear()
        rate_limit.reset_limits()

    def tearDown(self):
        get_rag_engine.cache_clear()
        rate_limit.reset_limits()

    def test_basic_mode_retrieves_and_answers(self):
        response = self.client.post(
            "/ask", json={"question": "What retrieval modes does this API support?", "mode": "basic"}
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "basic")
        self.assertGreater(body["retrieved_documents"], 0)
        self.assertTrue(body["sources"])
        self.assertTrue(body["answer"])  # non-empty, extractive in offline mode

    def test_multi_query_mode_falls_back_to_single_query_offline(self):
        response = self.client.post(
            "/ask", json={"question": "How does hybrid retrieval work?", "mode": "multi_query"}
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "multi_query")
        self.assertIsNone(body["rewritten_query"])
        self.assertGreater(body["retrieved_documents"], 0)

    def test_hybrid_mode_combines_semantic_and_keyword_hits(self):
        response = self.client.post(
            "/ask", json={"question": "What is contextual retrieval?", "mode": "hybrid"}
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "hybrid")
        self.assertGreater(body["retrieved_documents"], 0)

    def test_agentic_mode_skips_rewrite_offline(self):
        # No LLM available offline, so agentic mode can't rewrite a weak
        # query — it should degrade to the hybrid result instead of erroring.
        response = self.client.post(
            "/ask",
            json={"question": "Completely unrelated gibberish about zzz nowhere", "mode": "agentic"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "agentic")
        self.assertIsNone(body["rewritten_query"])

    def test_rejects_empty_question(self):
        response = self.client.post("/ask", json={"question": "", "mode": "basic"})

        self.assertEqual(response.status_code, 422)

    def test_stream_emits_meta_then_tokens_then_done(self):
        response = self.client.post(
            "/ask", json={"question": "What retrieval modes does this API support?", "mode": "basic", "stream": True}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/event-stream; charset=utf-8")

        events = [
            json.loads(line[len("data: ") :])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        self.assertEqual(events[0]["type"], "meta")
        self.assertEqual(events[0]["mode"], "basic")
        self.assertTrue(events[0]["sources"])
        self.assertEqual(events[-1]["type"], "done")
        token_events = [e for e in events if e["type"] == "token"]
        self.assertTrue(token_events)
        self.assertTrue("".join(e["text"] for e in token_events))


if __name__ == "__main__":
    unittest.main()

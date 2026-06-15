import unittest

from app.services import document_service
from evals import run_eval


class EvalRunnerTestCase(unittest.TestCase):
    def test_run_produces_expected_metrics(self):
        original_storage = document_service.STORAGE_DIR

        # results_path=None so the test does not overwrite the repo's results.md.
        results = run_eval.run(results_path=None)

        # Eval must restore the original storage root (isolation guarantee).
        self.assertEqual(document_service.STORAGE_DIR, original_storage)

        metrics = results["metrics"]
        for key in (
            "retrieval_hit_rate",
            "citation_presence_rate",
            "fallback_accuracy",
            "avg_latency_ms",
        ):
            self.assertIn(key, metrics)

        self.assertEqual(metrics["fallback_accuracy"], 1.0)
        self.assertEqual(metrics["citation_presence_rate"], 1.0)
        self.assertGreaterEqual(metrics["retrieval_hit_rate"], 0.75)
        self.assertGreater(metrics["avg_latency_ms"], 0.0)

        self.assertEqual(len(results["per_question"]), metrics["total_questions"])

    def test_results_markdown_has_stable_heading(self):
        results = run_eval.run(results_path=None)
        markdown = run_eval.format_results_md(results)

        self.assertIn("# DocuIntelAI RAG Evaluation Results", markdown)
        # No dynamic timestamp should leak into the report.
        self.assertNotIn("202", markdown.split("\n", 1)[0])


if __name__ == "__main__":
    unittest.main()

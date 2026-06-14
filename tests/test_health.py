import unittest

from fastapi.testclient import TestClient

from app.main import app


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_features_lists_advanced_modes(self):
        response = self.client.get("/features")
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("hybrid", body["retrieval_modes"])
        self.assertIn("agentic", body["retrieval_modes"])


if __name__ == "__main__":
    unittest.main()

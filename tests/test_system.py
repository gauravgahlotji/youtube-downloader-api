import unittest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestSystemEndpoints(unittest.TestCase):
    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("components", data)

    def test_status_endpoint(self):
        response = client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("server_status", data)
        self.assertIn("active_downloads", data)

    def test_metrics_endpoint(self):
        response = client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cpu", data)
        self.assertIn("memory", data)
        self.assertIn("disk", data)

    def test_version_endpoint(self):
        response = client.get("/version")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("version", data)
        self.assertIn("yt_dlp_version", data)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestDownloadAPI(unittest.TestCase):
    @patch('app.engine.yt_dlp_engine.YTDLPEngine.validate_and_extract_metadata')
    def test_metadata_extraction(self, mock_meta):
        mock_meta.return_value = {
            "title": "Test Video",
            "duration": 180,
            "uploader": "Test Channel",
            "thumbnail": "https://example.com/thumb.jpg",
            "formats": [],
            "subtitles": []
        }
        response = client.post("/api/v1/metadata", json={"url": "https://example.com/video"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["title"], "Test Video")

    @patch('app.routers.v1.download.run_video_job_task')
    def test_video_download_creation(self, mock_task):
        response = client.post("/api/v1/download/video", json={
            "url": "https://example.com/video",
            "quality": "720p",
            "format": "mp4"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "processing")

    @patch('app.routers.v1.download.run_audio_job_task')
    def test_audio_download_creation(self, mock_task):
        response = client.post("/api/v1/download/audio", json={
            "url": "https://example.com/audio",
            "format": "mp3",
            "bitrate": "192"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("job_id", data)

    @patch('app.routers.v1.download.run_video_job_task')
    def test_job_status_retrieval(self, mock_task):
        create_resp = client.post("/api/v1/download/video", json={"url": "https://example.com/video"})
        job_id = create_resp.json()["job_id"]

        status_resp = client.get(f"/api/v1/jobs/{job_id}")
        self.assertEqual(status_resp.status_code, 200)
        job_data = status_resp.json()["data"]
        self.assertEqual(job_data["job_id"], job_id)

    @patch('app.routers.v1.download.run_video_job_task')
    def test_job_cancellation(self, mock_task):
        create_resp = client.post("/api/v1/download/video", json={"url": "https://example.com/video"})
        job_id = create_resp.json()["job_id"]

        cancel_resp = client.post(f"/api/v1/jobs/{job_id}/cancel")
        self.assertEqual(cancel_resp.status_code, 200)
        self.assertTrue(cancel_resp.json()["success"])

    def test_dashboard_credentials_endpoint(self):
        resp = client.get("/api/v1/dashboard/credentials")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("api_url", data)
        self.assertIn("api_key", data)
        self.assertIn("secret_key", data)


if __name__ == "__main__":
    unittest.main()

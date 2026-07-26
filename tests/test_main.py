from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

client = TestClient(app)


def test_legacy_get_api_version():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json()['version'] == '0.2.0'


def test_docs_available():
    response = client.get('/docs')
    assert response.status_code == 200


def test_dashboard_available():
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert 'Developer Dashboard' in response.text


def test_download_video_api():
    response = client.post('/api/v1/download/video', json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "quality": "720p"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "job_id" in data
    assert data["status"] == "processing"


def test_get_job_status():
    # First create a job
    resp = client.post('/api/v1/download/video', json={"url": "https://example.com/video"})
    job_id = resp.json()["job_id"]

    status_resp = client.get(f'/api/v1/jobs/{job_id}')
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["job_id"] == job_id

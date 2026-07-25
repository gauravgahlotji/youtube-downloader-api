# YouTube Downloader API

Open Source YouTube Downloader REST API built with FastAPI and yt-dlp.

## Features

- **Asynchronous Task Queue**: Background video downloading powered by Celery and RabbitMQ.
- **Fast & Scalable**: High-performance REST API built with FastAPI.
- **Powerful Video Extraction**: Leverages `yt-dlp` to fetch metadata and download YouTube videos.
- **Built-in Web Interface**: Interactive web UI included for submitting download requests and viewing results.
- **Docker Ready**: Easy containerized deployment using Docker, Docker Compose, and Nginx.
- **Auto-generated Documentation**: OpenAPI / Swagger UI interactive API docs available out of the box.

## Installation

### Prerequisites
- Python 3.10+ (for local running) or Docker & Docker Compose (recommended)

### Option 1: Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/peter279k/youtube-downloader-api.git
   cd youtube-downloader-api
   ```

2. Build and start the services:
   ```bash
   docker compose build
   docker compose up -d
   ```

3. Access the application:
   - **Web UI**: `http://localhost/web/index_en.html`
   - **API Docs**: `http://localhost/docs`

### Option 2: Local Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure RabbitMQ server is running locally or configured via environment variables.

3. Start the FastAPI application:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Start the Celery worker in a separate terminal:
   ```bash
   celery -A workers.worker worker --loglevel=info
   ```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Get API version details |
| `GET` | `/download/` | Start asynchronous video download task (Query param: `url`) |
| `GET` | `/status/{job_id}` | Check job download status (`processing`, `completed`, `failed`) |
| `GET` | `/files/{filename}` | Stream / Download completed MP4 video file |

## Usage Examples

### 1. Check API Version
```bash
curl -X GET "http://localhost:8000/"
```
**Response:**
```json
{
  "version": "0.2.0"
}
```

### 2. Initiate Video Download
```bash
curl -X GET "http://localhost:8000/download/?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```
**Response:**
```json
{
  "job_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "status": "processing"
}
```

### 3. Check Download Status
```bash
curl -X GET "http://localhost:8000/status/c9bf9e57-1685-4c89-bafb-ff5af830be8a"
```
**Response (when ready):**
```json
{
  "status": "completed",
  "download_url": "/app/downloads/c9bf9e57-1685-4c89-bafb-ff5af830be8a.mp4"
}
```

### 4. Fetch Downloaded Video
```bash
curl -O "http://localhost:8000/files/c9bf9e57-1685-4c89-bafb-ff5af830be8a"
```

## License

This project is licensed under the [MIT License](LICENSE).

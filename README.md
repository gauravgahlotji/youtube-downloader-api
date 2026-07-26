# Enterprise YouTube Downloader API Platform

A high-performance **Enterprise Download Engine API Server** built with FastAPI and `yt-dlp`. 

This server acts as a dedicated download engine for **Laravel**, Node.js, Python, PHP, mobile apps, or any REST API client. End users interact with your main application (e.g. Laravel), while Laravel delegates all video/audio extraction and downloading tasks to this API.

---

## 🌟 Key Features

- 🎬 **Multi-Platform Support**: Downloads video, audio, thumbnails, playlists, and metadata from 1000+ supported sites (YouTube, Instagram, TikTok, Facebook, Twitter/X, Vimeo, etc.).
- 🚀 **17-Step Real-Time Event Pipeline**: Track download jobs step-by-step (`Job Created` → `Validating URL` → `Metadata Started` → `Thumbnail` → `Video Download` → `Audio Download` → `Merge` → `File Verification` → `File Ready` → `Cleanup`).
- ⏱ **Per-Second Progress JSON**: Returns progress percentage (0-100%), download speed (MB/s), ETA (seconds), and current step via REST polling, SSE stream, or Webhook callbacks.
- 🔒 **Enterprise Security**: HMAC SHA256 request signature validation (`X-Signature`), Timestamp verification (`X-Timestamp`), Nonce replay protection (`X-Nonce`), and Rate Limiting.
- 💻 **Developer Dashboard (Bootstrap 5)**: Built-in responsive dashboard with Dark/Light mode, live CPU/RAM/Disk gauges, active job monitors, structured JSON logs viewer, API Playground, and copy-to-clipboard code generators for **Laravel**, **PHP**, **Python**, **Node.js**, and **cURL**.
- 🛠 **Automated Cleanup & Storage Manager**: Temporary file TTL auto-cleaning, duplicate detection/caching, and file integrity verification.
- 📊 **Monitoring APIs**: Native `/health`, `/status`, `/metrics`, and `/version` endpoints for system diagnostics.

---

## 🚀 Quick Start

### 1. Installation & Local Running

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API Engine & Developer Dashboard
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Access the Developer Dashboard at: `http://localhost:8000/dashboard`  
Access OpenAPI / Swagger Docs at: `http://localhost:8000/docs`

### 2. Docker Compose (Production Deployment)

```bash
docker compose build
docker compose up -d
```

---

## 🔑 API Credentials

To integrate your Laravel or client application, grab your credentials from the Developer Dashboard (`http://localhost:8000/dashboard` -> API Credentials tab):

- **API Base URL**: `http://localhost:8000/api/v1`
- **API Key**: `yt_live_9f8d7c6b5a4e3d2c1b0a`
- **Secret Key**: `sec_k8j7h6g5f4d3s2a1_enterprise_secret`

---

## 🛠 Laravel Integration Example

Laravel only needs the `API URL`, `API Key`, and `Secret Key`. Add this helper service to your Laravel project (`app/Services/DownloadEngineService.php`):

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;

class DownloadEngineService
{
    protected string $apiUrl = 'http://localhost:8000/api/v1';
    protected string $apiKey = 'yt_live_9f8d7c6b5a4e3d2c1b0a';
    protected string $secretKey = 'sec_k8j7h6g5f4d3s2a1_enterprise_secret';

    public function startVideoDownload(string $videoUrl, string $quality = 'best', string $format = 'mp4')
    {
        $endpoint = $this->apiUrl . '/download/video';
        $timestamp = time();
        $nonce = uniqid('n_', true);
        
        $body = json_encode([
            'url' => $videoUrl,
            'quality' => $quality,
            'format' => $format,
            'webhook_url' => route('api.download.webhook')
        ]);

        $signature = hash_hmac('sha256', "{$this->apiKey}.{$timestamp}.{$nonce}.{$body}", $this->secretKey);

        $response = Http::withHeaders([
            'X-API-Key' => $this->apiKey,
            'X-Timestamp' => $timestamp,
            'X-Nonce' => $nonce,
            'X-Signature' => $signature,
            'Content-Type' => 'application/json',
        ])->withBody($body, 'application/json')->post($endpoint);

        return $response->json();
    }

    public function checkJobStatus(string $jobId)
    {
        $endpoint = $this->apiUrl . "/jobs/{$jobId}";
        $timestamp = time();
        $nonce = uniqid('n_', true);
        $signature = hash_hmac('sha256', "{$this->apiKey}.{$timestamp}.{$nonce}.", $this->secretKey);

        return Http::withHeaders([
            'X-API-Key' => $this->apiKey,
            'X-Timestamp' => $timestamp,
            'X-Nonce' => $nonce,
            'X-Signature' => $signature,
        ])->get($endpoint)->json();
    }
}
```

---

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/metadata` | Extract video title, duration, resolutions, formats & thumbnails |
| `POST` | `/api/v1/download/video` | Start video download job (supports quality & format selection) |
| `POST` | `/api/v1/download/audio` | Start audio extraction job (supports MP3, M4A, FLAC, bitrate) |
| `POST` | `/api/v1/download/thumbnail` | Fetch high-resolution video thumbnail image |
| `GET` | `/api/v1/jobs/{job_id}` | Retrieve per-second real-time job progress JSON |
| `GET` | `/api/v1/jobs/{job_id}/events` | SSE (Server-Sent Events) live progress stream |
| `POST` | `/api/v1/jobs/{job_id}/cancel` | Cancel active download job |
| `POST` | `/api/v1/jobs/{job_id}/retry` | Retry failed download job |
| `GET` | `/api/v1/files/{job_id}` | Stream / Download completed file |
| `GET` | `/health` | System & Storage health check |
| `GET` | `/status` | Active download count, queue status, uptime |
| `GET` | `/metrics` | CPU %, RAM %, Disk % utilization |
| `GET` | `/version` | API & yt-dlp core version details |

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

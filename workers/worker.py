import os
from pathlib import Path
from celery import Celery
from app.core.config import settings
from app.engine.yt_dlp_engine import YTDLPEngine
from app.services.job_manager import job_manager

celery = Celery(
    "worker",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "rpc://"),
)

@celery.task
def download_video_task(url: str, job_id: str, quality: str = "best", format_ext: str = "mp4") -> str:
    try:
        def update_cb(data):
            job_manager.update_job(job_id, data)

        filepath = YTDLPEngine.execute_video_download(
            url=url,
            job_id=job_id,
            quality=quality,
            format_ext=format_ext,
            update_callback=update_cb
        )
        job_manager.update_job(job_id, {
            "status": "completed",
            "progress": 100.0,
            "file_path": filepath,
            "download_url": f"/api/v1/files/{job_id}"
        })
        return filepath
    except Exception as e:
        log_path = settings.DOWNLOAD_DIR / f"{job_id}.log"
        with open(log_path, 'w') as f:
            f.write(f'{str(e)}\n')
        job_manager.update_job(job_id, {
            "status": "failed",
            "error": str(e)
        })
        raise e

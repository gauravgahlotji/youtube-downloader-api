import uuid
import os
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.routers.v1.download import VideoDownloadRequest, run_video_job_task
from app.services.job_manager import job_manager
from app.core.config import settings

legacy_router = APIRouter(tags=["Legacy Endpoints (v0.2.0)"])


@legacy_router.get("/")
async def get_api_version_legacy():
    return {"version": "0.2.0", "name": "Enterprise YouTube Downloader API Engine"}


@legacy_router.get("/download/")
async def download_video_legacy(url: str = Query(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    job_id = str(uuid.uuid4())
    req = VideoDownloadRequest(url=url, quality="best", format="mp4")
    job_manager.create_job(job_id, url, "video", req.model_dump())
    background_tasks.add_task(run_video_job_task, job_id, req)
    return {"job_id": job_id, "status": "processing"}


@legacy_router.get("/status/{job_id}")
async def check_status_legacy(job_id: str):
    job = job_manager.get_job(job_id)
    if job:
        if job["status"] == "completed":
            return {"status": "completed", "download_url": f"/files/{job_id}"}
        elif job["status"] == "failed":
            return {"status": "failed"}
        return {"status": "processing"}

    # Fallback to checking disk
    target_mp4 = settings.DOWNLOAD_DIR / f"{job_id}.mp4"
    target_log = settings.DOWNLOAD_DIR / f"{job_id}.log"
    if target_log.exists():
        return {"status": "failed"}
    if target_mp4.exists():
        return {"status": "completed", "download_url": str(target_mp4)}

    return {"status": "processing"}


@legacy_router.get("/files/{filename}")
async def get_file_legacy(filename: str):
    base_name = filename.replace(".mp4", "")
    target = settings.DOWNLOAD_DIR / f"{base_name}.mp4"
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not ready yet")

    return FileResponse(str(target), filename=f"{base_name}.mp4", media_type="video/mp4")

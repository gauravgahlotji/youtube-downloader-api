import os
import uuid
import json
import asyncio
from typing import Optional
from pydantic import BaseModel, HttpUrl
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.core.security import verify_request_security
from app.core.logger import log_event
from app.core.config import settings
from app.engine.yt_dlp_engine import YTDLPEngine
from app.engine.progress_hook import StepEvent
from app.services.job_manager import job_manager
from app.services.cleanup_service import cleanup_service
from app.services.webhook_notifier import send_webhook_async

router = APIRouter(prefix="/api/v1", tags=["Download Engine APIs"])


# Request Models
class MetadataRequest(BaseModel):
    url: str


class VideoDownloadRequest(BaseModel):
    url: str
    quality: Optional[str] = "best"
    format: Optional[str] = "mp4"
    include_subtitles: Optional[bool] = False
    sub_lang: Optional[str] = "en"
    webhook_url: Optional[str] = None


class AudioDownloadRequest(BaseModel):
    url: str
    format: Optional[str] = "mp3"
    bitrate: Optional[str] = "192"
    webhook_url: Optional[str] = None


class ThumbnailDownloadRequest(BaseModel):
    url: str


class PlaylistDownloadRequest(BaseModel):
    url: str
    quality: Optional[str] = "best"
    format: Optional[str] = "mp4"
    webhook_url: Optional[str] = None


def run_video_job_task(job_id: str, req: VideoDownloadRequest):
    def update_progress(data):
        job_manager.update_job(job_id, data)
        if req.webhook_url or settings.WEBHOOK_URL:
            send_webhook_async(req.webhook_url or settings.WEBHOOK_URL, data)

    try:
        # Step 1: Validating URL
        job_manager.update_job(job_id, {"current_step": StepEvent.VALIDATING_URL, "progress": 5.0})

        # Step 2: Metadata Extraction
        job_manager.update_job(job_id, {"current_step": StepEvent.METADATA_STARTED, "progress": 10.0})
        meta = YTDLPEngine.validate_and_extract_metadata(req.url)
        job_manager.update_job(job_id, {
            "current_step": StepEvent.METADATA_COMPLETED,
            "progress": 20.0,
            "metadata": meta
        })

        # Step 3: Thumbnail Extraction
        job_manager.update_job(job_id, {"current_step": StepEvent.THUMBNAIL_STARTED, "progress": 25.0})
        job_manager.update_job(job_id, {"current_step": StepEvent.THUMBNAIL_COMPLETED, "progress": 30.0})

        # Step 4: Video Download
        job_manager.update_job(job_id, {"current_step": StepEvent.VIDEO_DOWNLOAD_STARTED, "progress": 35.0})

        filepath = YTDLPEngine.execute_video_download(
            url=req.url,
            job_id=job_id,
            quality=req.quality or "best",
            format_ext=req.format or "mp4",
            include_subtitles=req.include_subtitles or False,
            sub_lang=req.sub_lang or "en",
            update_callback=update_progress
        )

        # Step 5: File Verification
        job_manager.update_job(job_id, {"current_step": StepEvent.FILE_VERIFICATION, "progress": 98.0})
        if not cleanup_service.verify_file(filepath):
            raise RuntimeError("Downloaded file verification failed (file missing or 0 bytes).")

        # Step 6: File Ready & Download Completed
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        final_data = {
            "status": "completed",
            "current_step": StepEvent.DOWNLOAD_COMPLETED,
            "progress": 100.0,
            "file_path": filepath,
            "file_name": filename,
            "file_size": filesize,
            "file_size_human": f"{round(filesize/1024/1024, 2)} MB",
            "download_url": f"/api/v1/files/{job_id}"
        }
        job_manager.update_job(job_id, final_data)

        if req.webhook_url or settings.WEBHOOK_URL:
            send_webhook_async(req.webhook_url or settings.WEBHOOK_URL, job_manager.get_job(job_id))

    except Exception as e:
        err_msg = str(e)
        log_event("ERROR_LOGS", "ERROR", f"Job {job_id} failed: {err_msg}")
        job_manager.update_job(job_id, {
            "status": "failed",
            "current_step": StepEvent.FAILED,
            "error": {
                "code": "DOWNLOAD_FAILED",
                "message": "Video processing encountered an engine error.",
                "reason": err_msg,
                "retryable": True
            }
        })
        if req.webhook_url or settings.WEBHOOK_URL:
            send_webhook_async(req.webhook_url or settings.WEBHOOK_URL, job_manager.get_job(job_id))


def run_audio_job_task(job_id: str, req: AudioDownloadRequest):
    def update_progress(data):
        job_manager.update_job(job_id, data)
        if req.webhook_url or settings.WEBHOOK_URL:
            send_webhook_async(req.webhook_url or settings.WEBHOOK_URL, data)

    try:
        job_manager.update_job(job_id, {"current_step": StepEvent.VALIDATING_URL, "progress": 5.0})
        meta = YTDLPEngine.validate_and_extract_metadata(req.url)
        job_manager.update_job(job_id, {
            "current_step": StepEvent.METADATA_COMPLETED,
            "progress": 20.0,
            "metadata": meta
        })
        job_manager.update_job(job_id, {"current_step": StepEvent.AUDIO_DOWNLOAD_STARTED, "progress": 35.0})

        filepath = YTDLPEngine.execute_audio_download(
            url=req.url,
            job_id=job_id,
            audio_format=req.format or "mp3",
            bitrate=req.bitrate or "192",
            update_callback=update_progress
        )

        job_manager.update_job(job_id, {"current_step": StepEvent.FILE_VERIFICATION, "progress": 98.0})
        if not cleanup_service.verify_file(filepath):
            raise RuntimeError("Audio file verification failed.")

        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        final_data = {
            "status": "completed",
            "current_step": StepEvent.DOWNLOAD_COMPLETED,
            "progress": 100.0,
            "file_path": filepath,
            "file_name": filename,
            "file_size": filesize,
            "file_size_human": f"{round(filesize/1024/1024, 2)} MB",
            "download_url": f"/api/v1/files/{job_id}"
        }
        job_manager.update_job(job_id, final_data)

        if req.webhook_url or settings.WEBHOOK_URL:
            send_webhook_async(req.webhook_url or settings.WEBHOOK_URL, job_manager.get_job(job_id))

    except Exception as e:
        err_msg = str(e)
        log_event("ERROR_LOGS", "ERROR", f"Audio job {job_id} failed: {err_msg}")
        job_manager.update_job(job_id, {
            "status": "failed",
            "current_step": StepEvent.FAILED,
            "error": {
                "code": "AUDIO_DOWNLOAD_FAILED",
                "message": "Audio processing failed.",
                "reason": err_msg,
                "retryable": True
            }
        })


@router.post("/metadata", dependencies=[Depends(verify_request_security)])
async def get_metadata(req: MetadataRequest):
    try:
        data = YTDLPEngine.validate_and_extract_metadata(req.url)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_URL",
                    "message": "Failed to extract metadata for the provided URL.",
                    "reason": str(e),
                    "retryable": False
                }
            }
        )


@router.post("/download/video", dependencies=[Depends(verify_request_security)])
async def download_video_endpoint(req: VideoDownloadRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job = job_manager.create_job(job_id, req.url, "video", req.model_dump(), req.webhook_url)
    background_tasks.add_task(run_video_job_task, job_id, req)
    return {"success": True, "job_id": job_id, "status": "processing", "message": "Video download job initiated."}


@router.post("/download/audio", dependencies=[Depends(verify_request_security)])
async def download_audio_endpoint(req: AudioDownloadRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job = job_manager.create_job(job_id, req.url, "audio", req.model_dump(), req.webhook_url)
    background_tasks.add_task(run_audio_job_task, job_id, req)
    return {"success": True, "job_id": job_id, "status": "processing", "message": "Audio download job initiated."}


@router.post("/download/thumbnail", dependencies=[Depends(verify_request_security)])
async def download_thumbnail_endpoint(req: ThumbnailDownloadRequest):
    job_id = str(uuid.uuid4())
    try:
        filepath = YTDLPEngine.execute_thumbnail_download(req.url, job_id)
        return {
            "success": True,
            "job_id": job_id,
            "status": "completed",
            "download_url": f"/api/v1/files/{job_id}?ext=jpg"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "THUMBNAIL_FAILED",
                    "message": "Thumbnail extraction failed.",
                    "reason": str(e),
                    "retryable": False
                }
            }
        )


@router.get("/jobs/{job_id}", dependencies=[Depends(verify_request_security)])
async def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job ID {job_id} not found.",
                    "reason": "Invalid or expired Job ID.",
                    "retryable": False
                }
            }
        )
    return {"success": True, "data": job}


@router.get("/jobs/{job_id}/events")
async def job_events_stream(job_id: str, request: Request):
    async def event_generator():
        queue = job_manager.subscribe(job_id)
        try:
            # Yield current state first
            initial_job = job_manager.get_job(job_id)
            if initial_job:
                yield f"data: {json.dumps(initial_job)}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(data)}\n\n"
                    if data.get("status") in ["completed", "failed", "cancelled"]:
                        break
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            job_manager.unsubscribe(job_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/jobs/{job_id}/cancel", dependencies=[Depends(verify_request_security)])
async def cancel_job_endpoint(job_id: str):
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail={"error": {"code": "JOB_NOT_FOUND", "message": "Job ID not found"}})
    return {"success": True, "message": "Job cancelled successfully."}


@router.post("/jobs/{job_id}/retry", dependencies=[Depends(verify_request_security)])
async def retry_job_endpoint(job_id: str, background_tasks: BackgroundTasks):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"code": "JOB_NOT_FOUND", "message": "Job ID not found"}})

    new_job_id = str(uuid.uuid4())
    job_type = job.get("type", "video")
    opts = job.get("options", {})
    opts["url"] = job.get("url")

    if job_type == "video":
        req = VideoDownloadRequest(**opts)
        job_manager.create_job(new_job_id, req.url, "video", req.model_dump(), req.webhook_url)
        background_tasks.add_task(run_video_job_task, new_job_id, req)
    else:
        req = AudioDownloadRequest(**opts)
        job_manager.create_job(new_job_id, req.url, "audio", req.model_dump(), req.webhook_url)
        background_tasks.add_task(run_audio_job_task, new_job_id, req)

    return {"success": True, "new_job_id": new_job_id, "status": "processing", "message": "Job retry initiated."}


@router.get("/files/{job_id}")
async def get_downloaded_file(job_id: str, ext: Optional[str] = None):
    # Check if job exists first
    job = job_manager.get_job(job_id)
    if job and job.get("file_path") and os.path.exists(job["file_path"]):
        return FileResponse(job["file_path"], filename=job.get("file_name"))

    # Fallback path search in download dir
    ext_list = [ext] if ext else ["mp4", "mp3", "m4a", "webm", "mkv", "jpg", "vtt"]
    for e in ext_list:
        target = settings.DOWNLOAD_DIR / f"{job_id}.{e}"
        if target.exists():
            media_type = "video/mp4" if e == "mp4" else "audio/mpeg" if e == "mp3" else "application/octet-stream"
            return FileResponse(str(target), filename=f"{job_id}.{e}", media_type=media_type)

    raise HTTPException(
        status_code=404,
        detail={
            "error": {
                "code": "FILE_NOT_FOUND",
                "message": "Requested download file is not ready or has expired.",
                "reason": "File missing in temp storage.",
                "retryable": False
            }
        }
    )

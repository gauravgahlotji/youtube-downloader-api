import time
import sys
import platform
import os
import yt_dlp
import yt_dlp.version
from fastapi import APIRouter
from app.core.config import settings
from app.services.cleanup_service import cleanup_service
from app.services.job_manager import job_manager

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

router = APIRouter(tags=["System & Monitoring"])

START_TIME = time.time()


def get_yt_dlp_ver() -> str:
    if hasattr(yt_dlp, "__version__"):
        return getattr(yt_dlp, "__version__")
    if hasattr(yt_dlp, "version") and hasattr(yt_dlp.version, "__version__"):
        return getattr(yt_dlp.version, "__version__")
    return "yt-dlp core"


@router.get("/health")
async def health_check():
    storage = cleanup_service.get_storage_metrics()
    is_healthy = storage["percent_used"] < 95.0
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": time.time(),
        "components": {
            "api_server": "online",
            "yt_dlp_engine": f"yt-dlp {get_yt_dlp_ver()}",
            "storage": {
                "status": "ok" if storage["percent_used"] < 90 else "warning",
                "percent_used": storage["percent_used"],
                "free_human": storage["free_human"]
            },
            "job_worker": "active"
        }
    }


@router.get("/status")
async def status_check():
    jobs = job_manager.list_jobs(limit=500)
    active_jobs = [j for j in jobs if j.get("status") == "processing"]
    completed_jobs = [j for j in jobs if j.get("status") == "completed"]
    failed_jobs = [j for j in jobs if j.get("status") == "failed"]
    uptime_seconds = int(time.time() - START_TIME)

    return {
        "server_status": "online",
        "uptime_seconds": uptime_seconds,
        "uptime_human": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s",
        "active_downloads": len(active_jobs),
        "queue_length": len(active_jobs),
        "completed_count": len(completed_jobs),
        "failed_count": len(failed_jobs),
        "total_jobs_processed": len(jobs),
        "max_concurrent_workers": settings.MAX_CONCURRENT_DOWNLOADS
    }


@router.get("/metrics")
async def metrics_check():
    if HAS_PSUTIL:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        cpu_data = {
            "percent_used": cpu_percent,
            "core_count": psutil.cpu_count(logical=True)
        }
        mem_data = {
            "total_human": f"{round(mem.total / (1024**3), 2)} GB",
            "used_human": f"{round(mem.used / (1024**3), 2)} GB",
            "percent_used": mem.percent
        }
    else:
        cpu_data = {"percent_used": 0.0, "core_count": os.cpu_count() or 1}
        mem_data = {"total_human": "Unknown", "used_human": "Unknown", "percent_used": 0.0}

    storage = cleanup_service.get_storage_metrics()
    jobs = job_manager.list_jobs(limit=1000)

    return {
        "cpu": cpu_data,
        "memory": mem_data,
        "disk": storage,
        "job_metrics": {
            "active_running": len([j for j in jobs if j.get("status") == "processing"]),
            "total_processed": len(jobs),
            "completed": len([j for j in jobs if j.get("status") == "completed"]),
            "failed": len([j for j in jobs if j.get("status") == "failed"])
        }
    }


@router.get("/version")
async def version_check():
    return {
        "api_name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "yt_dlp_version": get_yt_dlp_ver(),
        "python_version": sys.version.split()[0],
        "os_platform": platform.platform(),
        "environment": "production"
    }

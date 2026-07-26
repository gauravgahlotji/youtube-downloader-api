from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.core.logger import get_recent_logs
from app.services.job_manager import job_manager
from app.services.cleanup_service import cleanup_service

router = APIRouter(tags=["Developer Dashboard"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render_template_response(request: Request, name: str, context: dict):
    ctx = dict(context)
    ctx["request"] = request
    try:
        return templates.TemplateResponse(request=request, name=name, context=ctx)
    except Exception:
        return templates.TemplateResponse(name, ctx)


class SettingsUpdateRequest(BaseModel):
    enforce_signature: Optional[bool] = None
    temp_file_ttl: Optional[int] = None
    max_concurrent: Optional[int] = None
    rate_limit: Optional[int] = None
    webhook_url: Optional[str] = None


@router.get("/")
@router.get("/dashboard")
async def render_dashboard(request: Request):
    return render_template_response(request, "dashboard.html", {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "api_key": settings.API_KEY,
        "secret_key": settings.SECRET_KEY,
        "webhook_url": settings.WEBHOOK_URL,
        "base_url": str(request.base_url).rstrip('/')
    })


@router.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    jobs = job_manager.list_jobs(limit=100)
    storage = cleanup_service.get_storage_metrics()
    active_jobs = [j for j in jobs if j.get("status") == "processing"]

    return {
        "active_downloads": len(active_jobs),
        "queue_count": len(active_jobs),
        "completed_jobs": len([j for j in jobs if j.get("status") == "completed"]),
        "failed_jobs": len([j for j in jobs if j.get("status") == "failed"]),
        "storage": storage,
        "running_jobs_list": jobs[:10]
    }


@router.get("/api/v1/dashboard/logs")
async def get_dashboard_logs(category: Optional[str] = None, level: Optional[str] = None, limit: int = 100):
    logs = get_recent_logs(category=category, level=level, limit=limit)
    return {"success": True, "logs": logs}


@router.get("/api/v1/dashboard/credentials")
async def get_dashboard_credentials(request: Request):
    base_url = str(request.base_url).rstrip('/')
    return {
        "api_url": f"{base_url}/api/v1",
        "api_key": settings.API_KEY,
        "secret_key": settings.SECRET_KEY,
        "webhook_url": settings.WEBHOOK_URL or f"{base_url}/api/v1/webhooks/dummy"
    }


@router.post("/api/v1/dashboard/settings")
async def update_dashboard_settings(req: SettingsUpdateRequest):
    if req.enforce_signature is not None:
        settings.SECURITY_ENFORCE_SIGNATURE = req.enforce_signature
    if req.temp_file_ttl is not None:
        settings.TEMP_FILE_TTL_MINUTES = req.temp_file_ttl
    if req.max_concurrent is not None:
        settings.MAX_CONCURRENT_DOWNLOADS = req.max_concurrent
    if req.rate_limit is not None:
        settings.RATE_LIMIT_REQUESTS_PER_MINUTE = req.rate_limit
    if req.webhook_url is not None:
        settings.WEBHOOK_URL = req.webhook_url

    return {
        "success": True,
        "message": "Dashboard settings updated successfully.",
        "settings": {
            "enforce_signature": settings.SECURITY_ENFORCE_SIGNATURE,
            "temp_file_ttl_minutes": settings.TEMP_FILE_TTL_MINUTES,
            "max_concurrent_downloads": settings.MAX_CONCURRENT_DOWNLOADS,
            "rate_limit_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            "webhook_url": settings.WEBHOOK_URL
        }
    }

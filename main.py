import asyncio
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_pagination import add_pagination

from app.core.config import settings
from app.core.rate_limiter import rate_limiter_middleware
from app.core.logger import log_event
from app.services.cleanup_service import cleanup_service
from app.routers import (
    legacy_router,
    download_v1_router,
    system_v1_router,
    dashboard_v1_router
)

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    contact={
        "name": "Enterprise API Support",
        "email": "support@enterprise-api.local",
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=origins,
    allow_headers=origins,
)

# Rate Limiter Middleware
@app.middleware("http")
async def apply_rate_limiter(request: Request, call_next):
    return await rate_limiter_middleware(request, call_next)

# Mount Static Files & Routes
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if not os.path.exists(static_dir):
    static_dir = os.path.join(os.path.dirname(__file__), "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount Routers
app.include_router(dashboard_v1_router)
app.include_router(download_v1_router)
app.include_router(system_v1_router)
app.include_router(legacy_router)

# Structured JSON Error Handler
@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    err_msg = str(exc)
    log_event("ERROR_LOGS", "ERROR", f"Unhandled exception on {request.url.path}: {err_msg}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal processing error occurred.",
                "reason": "Unexpected server exception.",
                "retryable": True
            }
        }
    )

# Periodic Auto-Cleanup Task
@app.on_event("startup")
async def startup_event():
    log_event("API_LOGS", "INFO", f"Enterprise API Engine v{settings.API_VERSION} started.")
    
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            try:
                removed = cleanup_service.cleanup_old_files()
                if removed > 0:
                    log_event("PERFORMANCE_LOGS", "INFO", f"Automated cleanup removed {removed} old temporary files.")
            except Exception as e:
                log_event("ERROR_LOGS", "WARN", f"Periodic cleanup error: {str(e)}")

    asyncio.create_task(periodic_cleanup())

add_pagination(app)

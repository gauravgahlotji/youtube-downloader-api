from app.routers.legacy import legacy_router
from app.routers.v1.download import router as download_v1_router
from app.routers.v1.system import router as system_v1_router
from app.routers.v1.dashboard import router as dashboard_v1_router

__all__ = ["legacy_router", "download_v1_router", "system_v1_router", "dashboard_v1_router"]

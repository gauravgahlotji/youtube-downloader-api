import os
import time
from pathlib import Path
from typing import Dict, Any
from app.core.config import settings
from app.core.logger import log_event

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class CleanupService:
    @staticmethod
    def cleanup_old_files() -> int:
        ttl_seconds = settings.TEMP_FILE_TTL_MINUTES * 60
        now = time.time()
        removed_count = 0

        if not settings.DOWNLOAD_DIR.exists():
            return 0

        for file_path in settings.DOWNLOAD_DIR.iterdir():
            if file_path.is_file():
                file_age = now - file_path.stat().st_mtime
                if file_age > ttl_seconds:
                    try:
                        file_path.unlink()
                        removed_count += 1
                        log_event("PERFORMANCE_LOGS", "INFO", f"Auto-cleaned temp file: {file_path.name}")
                    except Exception as e:
                        log_event("ERROR_LOGS", "WARN", f"Failed to clean temp file {file_path.name}: {str(e)}")

        return removed_count

    @staticmethod
    def get_storage_metrics() -> Dict[str, Any]:
        target = settings.DOWNLOAD_DIR if settings.DOWNLOAD_DIR.exists() else Path(".")
        if HAS_PSUTIL:
            usage = psutil.disk_usage(str(target))
            return {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total_human": f"{round(usage.total / (1024**3), 2)} GB",
                "used_human": f"{round(usage.used / (1024**3), 2)} GB",
                "free_human": f"{round(usage.free / (1024**3), 2)} GB",
                "percent_used": usage.percent
            }
        else:
            # Fallback storage estimation using os.statvfs or shutil.disk_usage
            import shutil
            total, used, free = shutil.disk_usage(str(target))
            percent = round((used / total * 100), 2) if total > 0 else 0.0
            return {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "total_human": f"{round(total / (1024**3), 2)} GB",
                "used_human": f"{round(used / (1024**3), 2)} GB",
                "free_human": f"{round(free / (1024**3), 2)} GB",
                "percent_used": percent
            }

    @staticmethod
    def verify_file(filepath: str) -> bool:
        if not filepath or not os.path.exists(filepath):
            return False
        if os.path.getsize(filepath) <= 0:
            return False
        return True


cleanup_service = CleanupService()

import time
from typing import Dict, Any, Callable


class StepEvent:
    JOB_CREATED = "Job Created"
    VALIDATING_URL = "Validating URL"
    METADATA_STARTED = "Metadata Started"
    METADATA_COMPLETED = "Metadata Completed"
    THUMBNAIL_STARTED = "Thumbnail Started"
    THUMBNAIL_COMPLETED = "Thumbnail Completed"
    VIDEO_DOWNLOAD_STARTED = "Video Download Started"
    AUDIO_DOWNLOAD_STARTED = "Audio Download Started"
    DOWNLOAD_PROGRESS = "Download Progress"
    MERGE_STARTED = "Merge Started"
    MERGE_COMPLETED = "Merge Completed"
    FILE_VERIFICATION = "File Verification"
    FILE_READY = "File Ready"
    DOWNLOAD_COMPLETED = "Download Completed"
    TEMP_CLEANUP = "Temporary File Cleanup"
    FAILED = "Failed"


def format_bytes(size: int) -> str:
    if not size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


class YTDLPProgressHook:
    def __init__(self, job_id: str, update_callback: Callable[[Dict[str, Any]], None]):
        self.job_id = job_id
        self.update_callback = update_callback
        self.last_update_time = 0

    def __call__(self, d: Dict[str, Any]):
        now = time.time()
        # Rate-limit updates to once per second unless finished/error
        status = d.get('status')
        if status != 'finished' and status != 'error' and (now - self.last_update_time < 0.8):
            return

        self.last_update_time = now

        if status == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0) or 0
            eta = d.get('eta', 0) or 0

            percent = round((downloaded / total * 100), 2) if total > 0 else 0.0

            speed_human = f"{format_bytes(speed)}/s" if speed else "0 B/s"
            downloaded_human = format_bytes(downloaded)
            total_human = format_bytes(total) if total else "Unknown"

            progress_data = {
                "job_id": self.job_id,
                "status": "processing",
                "current_step": StepEvent.DOWNLOAD_PROGRESS,
                "progress": percent,
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "downloaded_bytes_human": downloaded_human,
                "total_bytes_human": total_human,
                "speed": speed,
                "speed_human": speed_human,
                "eta": eta,
                "eta_human": f"{eta}s" if eta else "0s"
            }
            self.update_callback(progress_data)

        elif status == 'finished':
            progress_data = {
                "job_id": self.job_id,
                "status": "processing",
                "current_step": StepEvent.MERGE_STARTED,
                "progress": 95.0,
                "downloaded_bytes_human": "100%",
                "speed_human": "0 B/s",
                "eta": 0,
                "eta_human": "0s"
            }
            self.update_callback(progress_data)

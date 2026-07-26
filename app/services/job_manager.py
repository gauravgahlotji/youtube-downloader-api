import time
import asyncio
from typing import Dict, Any, List, Optional
from app.engine.progress_hook import StepEvent
from app.core.logger import log_event


class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}

    def create_job(
        self,
        job_id: str,
        url: str,
        job_type: str = "video",
        options: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        job_data = {
            "job_id": job_id,
            "url": url,
            "type": job_type,
            "status": "processing",
            "current_step": StepEvent.JOB_CREATED,
            "progress": 0.0,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "downloaded_bytes_human": "0 B",
            "total_bytes_human": "0 B",
            "speed": 0,
            "speed_human": "0 B/s",
            "eta": 0,
            "eta_human": "0s",
            "created_at": time.time(),
            "updated_at": time.time(),
            "file_path": None,
            "file_name": None,
            "file_size": 0,
            "metadata": None,
            "options": options or {},
            "webhook_url": webhook_url,
            "error": None,
            "retry_count": 0
        }
        self.jobs[job_id] = job_data
        log_event("DOWNLOAD_LOGS", "INFO", f"Job created: {job_id} ({job_type}) for {url}")
        self._notify_subscribers(job_id, job_data)
        return job_data

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if job_id not in self.jobs:
            return None
        job = self.jobs[job_id]
        job.update(updates)
        job["updated_at"] = time.time()
        self._notify_subscribers(job_id, job)
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def list_jobs(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        all_jobs = list(self.jobs.values())
        if status:
            all_jobs = [j for j in all_jobs if j.get("status") == status]
        all_jobs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return all_jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = "cancelled"
            self.jobs[job_id]["current_step"] = "Cancelled"
            self.jobs[job_id]["updated_at"] = time.time()
            log_event("DOWNLOAD_LOGS", "WARN", f"Job cancelled: {job_id}")
            self._notify_subscribers(job_id, self.jobs[job_id])
            return True
        return False

    def subscribe(self, job_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if job_id not in self.subscribers:
            self.subscribers[job_id] = []
        self.subscribers[job_id].append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        if job_id in self.subscribers and queue in self.subscribers[job_id]:
            self.subscribers[job_id].remove(queue)

    def _notify_subscribers(self, job_id: str, data: Dict[str, Any]):
        if job_id in self.subscribers:
            for queue in self.subscribers[job_id]:
                try:
                    queue.put_nowait(data)
                except Exception:
                    pass


job_manager = JobManager()

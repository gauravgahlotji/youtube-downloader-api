import httpx
import asyncio
from typing import Dict, Any
from app.core.logger import log_event
from app.core.config import settings


async def dispatch_webhook(webhook_url: str, payload: Dict[str, Any]):
    if not webhook_url:
        webhook_url = settings.WEBHOOK_URL
    if not webhook_url:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            log_event(
                "API_LOGS",
                "INFO",
                f"Webhook sent to {webhook_url} for job {payload.get('job_id')} - Status {response.status_code}"
            )
    except Exception as e:
        log_event(
            "ERROR_LOGS",
            "WARN",
            f"Webhook dispatch failed for {webhook_url}: {str(e)}"
        )


def send_webhook_async(webhook_url: str, payload: Dict[str, Any]):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(dispatch_webhook(webhook_url, payload))
    except RuntimeError:
        # If no running event loop in background thread (e.g. Celery)
        pass

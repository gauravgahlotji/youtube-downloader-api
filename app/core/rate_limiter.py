import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException
from app.core.config import settings

# Client IP / API Key request timestamps store
request_history: Dict[str, List[float]] = defaultdict(list)


async def rate_limiter_middleware(request: Request, call_next):
    # Exempt static files and docs from rate limiting
    path = request.url.path
    if path.startswith("/static") or path.startswith("/docs") or path.startswith("/openapi.json") or path == "/dashboard":
        return await call_next(request)

    client_identifier = request.headers.get("X-API-Key") or request.client.host if request.client else "unknown"
    now = time.time()

    # Clean old requests older than 60 seconds
    timestamps = request_history[client_identifier]
    timestamps = [t for t in timestamps if now - t < 60]
    request_history[client_identifier] = timestamps

    if len(timestamps) >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {settings.RATE_LIMIT_REQUESTS_PER_MINUTE} requests per minute exceeded.",
                    "reason": "Too many requests. Please wait before making more requests.",
                    "retryable": True
                }
            }
        )

    request_history[client_identifier].append(now)
    return await call_next(request)

import hmac
import hashlib
import time
from typing import Optional, Set
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from app.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)

# Replay protection nonce store
seen_nonces: Set[str] = set()
MAX_NONCES_STORED = 10000


def calculate_signature(api_key: str, secret_key: str, timestamp: str, nonce: str, payload: str = "") -> str:
    """
    Calculates HMAC SHA256 signature.
    Message format: api_key + "." + timestamp + "." + nonce + "." + payload
    """
    raw = f"{api_key}.{timestamp}.{nonce}.{payload}".encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def verify_api_key(
    api_key_header: Optional[str] = Depends(API_KEY_HEADER),
    api_key_query: Optional[str] = Depends(API_KEY_QUERY)
) -> str:
    key = api_key_header or api_key_query
    if not key:
        # If signature is not strictly enforced, default to settings.API_KEY
        if not settings.SECURITY_ENFORCE_SIGNATURE:
            return settings.API_KEY
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "X-API-Key header or api_key query parameter is required.",
                    "reason": "Unauthorized access attempt without API credentials.",
                    "retryable": False
                }
            }
        )
    if key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "The provided API Key is invalid or inactive.",
                    "reason": "API Key mismatch.",
                    "retryable": False
                }
            }
        )
    return key


async def verify_request_security(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Validates API Key, Timestamp, Nonce, and HMAC Signature.
    """
    if not settings.SECURITY_ENFORCE_SIGNATURE:
        return True

    timestamp = request.headers.get("X-Timestamp") or request.query_params.get("timestamp")
    nonce = request.headers.get("X-Nonce") or request.query_params.get("nonce")
    signature = request.headers.get("X-Signature") or request.query_params.get("signature")

    if not timestamp or not nonce or not signature:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_SECURITY_HEADERS",
                    "message": "X-Timestamp, X-Nonce, and X-Signature headers are required when signature enforcement is enabled.",
                    "reason": "Incomplete HMAC signature payload.",
                    "retryable": False
                }
            }
        )

    # 1. Timestamp Validation
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > settings.SECURITY_TIMESTAMP_WINDOW_SECONDS:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "code": "TIMESTAMP_EXPIRED",
                        "message": f"Request timestamp is outside the allowed window ({settings.SECURITY_TIMESTAMP_WINDOW_SECONDS}s).",
                        "reason": f"Current server time: {now}, Request time: {ts}",
                        "retryable": True
                    }
                }
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_TIMESTAMP",
                    "message": "Timestamp must be a valid Unix integer.",
                    "reason": "Malformed timestamp header.",
                    "retryable": False
                }
            }
        )

    # 2. Nonce Validation (Replay Protection)
    if nonce in seen_nonces:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "REPLAY_ATTACK_DETECTED",
                    "message": "This request nonce has already been processed.",
                    "reason": "Duplicate nonce detected.",
                    "retryable": False
                }
            }
        )

    if len(seen_nonces) > MAX_NONCES_STORED:
        seen_nonces.clear()
    seen_nonces.add(nonce)

    # 3. Signature Verification
    body_text = ""
    if request.method in ["POST", "PUT", "PATCH"]:
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8")

    expected_sig = calculate_signature(api_key, settings.SECRET_KEY, str(timestamp), nonce, body_text)
    if not hmac.compare_digest(expected_sig.lower(), signature.lower()):
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "INVALID_SIGNATURE",
                    "message": "HMAC SHA256 signature verification failed.",
                    "reason": "Computed signature does not match header signature.",
                    "retryable": False
                }
            }
        )

    return True

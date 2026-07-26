import logging
import json
import time
from collections import deque
from typing import Dict, Any, List, Optional

# Circular buffer for dashboard live logs
LOG_BUFFER: deque = deque(maxlen=500)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "category": getattr(record, "category", "API_LOGS"),
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data
        
        LOG_BUFFER.append(log_entry)
        return json.dumps(log_entry)


def setup_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    return logger


logger = setup_logger("downloader_api")


def log_event(category: str, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
    lvl = getattr(logging, level.upper(), logging.INFO)
    extra_dict = {"category": category, "extra_data": extra or {}}
    logger.log(lvl, message, extra=extra_dict)


def get_recent_logs(category: Optional[str] = None, level: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    logs = list(LOG_BUFFER)
    if category:
        logs = [l for l in logs if l.get("category") == category]
    if level:
        logs = [l for l in logs if l.get("level") == level.upper()]
    return logs[-limit:]

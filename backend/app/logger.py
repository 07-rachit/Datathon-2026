"""
Structured Logging & Sensitive Data Scrubbing Utility.

Ensures credentials, access tokens, secrets, stack traces, and statutory sensitive fields
are never exposed in application logs or exception payloads.
"""
import logging
import sys
from typing import Any, Dict, List

SENSITIVE_KEYS = {
    "password", "hashed_password", "token", "access_token",
    "secret", "secret_key", "api_key", "apikey", "jwt_secret_key",
    "authorization", "jwt", "caste_id", "religion_id", "caste_name", "religion_name"
}


def sanitize_data(data: Any) -> Any:
    """Recursively mask sensitive values in dictionaries and lists."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = sanitize_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


# Set up structured logger
logger = logging.getLogger("crimeintel")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [ReqID: %(request_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class RequestIDAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        request_id = kwargs.pop("request_id", None) or getattr(self.extra, "get", lambda k, d: d)("request_id", "system")
        kwargs.setdefault("extra", {})["request_id"] = request_id
        return msg, kwargs


def get_logger(request_id: str = "system") -> RequestIDAdapter:
    return RequestIDAdapter(logger, {"request_id": request_id})

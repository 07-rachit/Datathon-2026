"""
Rate-limiting singleton (slowapi / limits library).

Import `limiter` in routers and apply the @limiter.limit() decorator.
The middleware is registered in main.py.

Default limits (configurable via env vars):
  RATE_LIMIT_AUTH  — applied to login endpoint  (default: 10/minute)
  RATE_LIMIT_CHAT  — applied to chat send        (default: 30/minute)
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],          # no blanket limit; apply per-route
    storage_uri="memory://",    # in-process; swap for redis:// in prod
)

RATE_AUTH = os.getenv("RATE_LIMIT_AUTH", "10/minute")
RATE_CHAT = os.getenv("RATE_LIMIT_CHAT", "30/minute")

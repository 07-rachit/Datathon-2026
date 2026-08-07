"""
Centralized Error Handling Middleware and Exception Handlers.

Returns a standardized JSON response format for success and failure cases:
{
  "success": False,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "status_code": 422,
    "details": [...],
    "timestamp": "...",
    "request_id": "..."
  },
  "detail": "..."
}
"""
import uuid
from typing import Any, Dict
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded

from app.errors import (
    AppException, ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, BusinessRuleError, RateLimitError,
    DatabaseError, InternalServerError
)
from app.logger import get_logger, sanitize_data


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique request ID into every HTTP request context and response header."""
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


def _get_req_id(request: Request) -> str:
    return getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    req_id = _get_req_id(request)
    log = get_logger(req_id)
    log.warning(f"{exc.error_code} [{exc.status_code}]: {exc.message} | Path: {request.url.path}")
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict(req_id))


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = _get_req_id(request)
    log = get_logger(req_id)
    
    details = []
    for err in exc.errors():
        loc = " -> ".join([str(x) for x in err.get("loc", [])])
        msg = err.get("msg", "Invalid value")
        details.append({
            "field": loc,
            "message": msg,
            "type": err.get("type", "value_error"),
        })

    log.info(f"VALIDATION_ERROR [422] on {request.url.path}: {sanitize_data(details)}")
    val_err = ValidationError(message="Payload schema validation failed", details=details)
    return JSONResponse(status_code=val_err.status_code, content=val_err.to_dict(req_id))


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = _get_req_id(request)
    log = get_logger(req_id)
    
    status_code = exc.status_code
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    
    # Map HTTP status codes to typed errors
    if status_code == status.HTTP_401_UNAUTHORIZED:
        app_err = AuthenticationError(message=detail)
    elif status_code == status.HTTP_403_FORBIDDEN:
        app_err = AuthorizationError(message=detail)
    elif status_code == status.HTTP_404_NOT_FOUND:
        app_err = ResourceNotFoundError(message=detail)
    elif status_code == status.HTTP_409_CONFLICT:
        app_err = ConflictError(message=detail)
    elif status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        app_err = ValidationError(message=detail)
    elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        app_err = RateLimitError(message=detail)
    elif status_code >= 500:
        app_err = InternalServerError(message=detail)
    else:
        app_err = BusinessRuleError(message=detail, status_code=status_code)

    log.warning(f"HTTPException [{status_code}] on {request.url.path}: {detail}")
    return JSONResponse(status_code=status_code, content=app_err.to_dict(req_id))


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    req_id = _get_req_id(request)
    log = get_logger(req_id)
    log.warning(f"Rate limit exceeded on {request.url.path}")
    err = RateLimitError(message="Too many requests. Please slow down and try again.")
    return JSONResponse(status_code=429, content=err.to_dict(req_id))


async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    req_id = _get_req_id(request)
    log = get_logger(req_id)
    # Log sanitized error message internally, never expose raw SQL/connection strings to client
    log.error(f"Database error on {request.url.path}: {str(exc)[:200]}")
    err = DatabaseError(message="A database operation error occurred. Request aborted safely.")
    return JSONResponse(status_code=500, content=err.to_dict(req_id))


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = _get_req_id(request)
    log = get_logger(req_id)
    log.exception(f"Unhandled server exception on {request.url.path}: {str(exc)[:300]}")
    err = InternalServerError(message="An internal server error occurred.")
    return JSONResponse(status_code=500, content=err.to_dict(req_id))

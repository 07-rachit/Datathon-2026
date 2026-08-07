"""
Typed Error Classes and Standardized Response Envelopes.

Provides a unified error hierarchy (AppException) with consistent HTTP status codes,
error codes, human-readable messages, field-level validation details, timestamps,
and request tracking IDs.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


class AppException(Exception):
    """Base application exception with standardized JSON error formatting."""
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "BUSINESS_RULE_ERROR",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []

    def to_dict(self, request_id: str = "") -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "status_code": self.status_code,
                "details": self.details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            },
            "detail": self.message,  # Backwards compatibility for standard FastAPI clients
        }


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=422, error_code="VALIDATION_ERROR", details=details)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=401, error_code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(AppException):
    def __init__(self, message: str = "Permission denied", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=403, error_code="AUTHORIZATION_ERROR", details=details)


class ResourceNotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=404, error_code="RESOURCE_NOT_FOUND", details=details)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict or duplicate action", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=409, error_code="CONFLICT_ERROR", details=details)


class BusinessRuleError(AppException):
    def __init__(self, message: str = "Business rule violation", status_code: int = 400, details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=status_code, error_code="BUSINESS_RULE_ERROR", details=details)


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=429, error_code="RATE_LIMIT_ERROR", details=details)


class DatabaseError(AppException):
    def __init__(self, message: str = "Database operation failed", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=500, error_code="DATABASE_ERROR", details=details)


class InternalServerError(AppException):
    def __init__(self, message: str = "Internal server error", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, status_code=500, error_code="INTERNAL_SERVER_ERROR", details=details)

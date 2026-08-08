"""
Centralized Persistent Activity History Framework.

Provides automatic HTTP request interceptor middleware and helper functions
to record all significant operations (AI outputs, case edits, citizen report actions,
task updates, imports, exports, auth events) into persistent searchable history.
"""
import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models
from app.logger import sanitize_data, get_logger


ROUTE_ACTION_MAP = {
    ("/api/cases", "POST"): ("case_created", "cases", "case", "Created new crime case file"),
    ("/api/citizen-reports", "POST"): ("citizen_report_submitted", "citizen_reports", "citizen_report", "Submitted public citizen report"),
    ("/api/chat/sessions", "POST"): ("ai_session_created", "ai_assistant", "chat_session", "Created AI investigation session"),
    ("/api/import/cases/csv", "POST"): ("csv_cases_imported", "import", "case", "Executed bulk CSV case ingestion"),
    ("/api/admin/users", "POST"): ("user_created", "admin", "user", "Created new platform user account"),
    ("/api/finance/transactions", "POST"): ("transaction_created", "finance", "financial_transaction", "Log financial transfer record"),
}


def record_activity(
    db: Session,
    activity_type: str,
    module: str,
    title: str,
    description: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    status: str = "success",
    tags: Optional[List[str]] = None,
    related_resources: Optional[List[Dict[str, Any]]] = None,
    execution_duration_ms: Optional[float] = None,
) -> models.ActivityHistory:
    """
    Record an immutable activity log entry into persistent database history.
    Automatically scrubs sensitive data fields before JSON serialization.
    """
    sanitized_meta = sanitize_data(metadata or {})
    sanitized_res = sanitize_data(related_resources or [])
    
    activity = models.ActivityHistory(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        activity_type=activity_type,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        description=description,
        metadata_json=json.dumps(sanitized_meta) if sanitized_meta else None,
        status=status,
        tags=json.dumps(tags or [module, activity_type]),
        related_resources=json.dumps(sanitized_res) if sanitized_res else None,
        execution_duration_ms=execution_duration_ms,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def _get_db_session():
    try:
        from app.database import get_db
        from app.main import app
        if get_db in app.dependency_overrides:
            override = app.dependency_overrides[get_db]
            gen = override()
            return next(gen), False
    except Exception:
        pass
    return SessionLocal(), True


class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    """Automatically logs HTTP API actions into persistent activity history."""
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.perf_counter()
        path = request.url.path
        method = request.method

        should_log = (
            method in ("POST", "PUT", "PATCH", "DELETE") or
            (method == "GET" and any(p in path for p in ["/export/", "/analyze", "/predict"]))
        ) and not path.endswith("/health") and not path.startswith("/assets") and not path.startswith("/api/activity-history")

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if should_log:
            try:
                db, is_owned = _get_db_session()
                try:
                    user_id = getattr(request.state, "user_id", None)
                    user_name = getattr(request.state, "user_name", None)
                    user_role = getattr(request.state, "user_role", None)

                    key = (path, method)
                    match = ROUTE_ACTION_MAP.get(key)
                    if match:
                        act_type, mod, ent_type, title_def = match
                        title = title_def
                    else:
                        path_parts = [p for p in path.split("/") if p and p != "api"]
                        mod = path_parts[0] if path_parts else "system"
                        ent_type = path_parts[0][:-1] if path_parts and path_parts[0].endswith("s") else "resource"
                        act_type = f"{method.lower()}_{mod}"
                        title = f"{method} operation on {mod}"

                    status_str = "success" if (200 <= response.status_code < 400) else "failed"

                    record_activity(
                        db=db,
                        activity_type=act_type,
                        module=mod,
                        title=title,
                        description=f"HTTP {method} {path} completed with status {response.status_code}",
                        user_id=user_id,
                        user_name=user_name,
                        user_role=user_role,
                        entity_type=ent_type,
                        metadata={
                            "path": path,
                            "method": method,
                            "status_code": response.status_code,
                            "query_params": dict(request.query_params),
                        },
                        status=status_str,
                        execution_duration_ms=duration_ms,
                    )
                finally:
                    if is_owned:
                        db.close()
            except Exception as e:
                log = get_logger("activity_middleware")
                log.error(f"Failed to record activity log: {e}")

        return response

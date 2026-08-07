"""
Activity History REST API Endpoints.

Provides searchable, paginated, filtered, and detailed access to persistent system activities,
with role-based access control, admin-only deletion, and summary metrics.
"""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app import models, schemas, auth
from app.errors import ResourceNotFoundError, AuthorizationError

router = APIRouter(prefix="/api/activity-history", tags=["activity-history"])


def _format_activity_out(act: models.ActivityHistory) -> schemas.ActivityHistoryOut:
    meta = None
    if act.metadata_json:
        try:
            meta = json.loads(act.metadata_json)
        except Exception:
            meta = {"raw": act.metadata_json}

    tags_list = []
    if act.tags:
        try:
            tags_list = json.loads(act.tags)
        except Exception:
            tags_list = [act.tags]

    resources = []
    if act.related_resources:
        try:
            resources = json.loads(act.related_resources)
        except Exception:
            resources = []

    return schemas.ActivityHistoryOut(
        id=act.id,
        timestamp=act.timestamp,
        user_id=act.user_id,
        user_name=act.user_name or (act.user.name if act.user else "System"),
        user_role=act.user_role or (act.user.role.value if act.user and act.user.role else "system"),
        activity_type=act.activity_type,
        module=act.module,
        entity_type=act.entity_type,
        entity_id=act.entity_id,
        title=act.title,
        description=act.description,
        metadata_json=meta,
        status=act.status,
        tags=tags_list,
        related_resources=resources,
        execution_duration_ms=act.execution_duration_ms,
    )


@router.get("", response_model=schemas.ActivityHistoryListResponse)
def list_activity_history(
    q: Optional[str] = Query(None, description="Free text search across title, description, module, type, entity, user"),
    activity_type: Optional[str] = Query(None, description="Filter by activity_type"),
    module: Optional[str] = Query(None, description="Filter by module (e.g. cases, ai_assistant, citizen_reports)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity_type"),
    entity_id: Optional[str] = Query(None, description="Filter by specific entity ID"),
    status: Optional[str] = Query(None, description="Filter by status: success, failed, warning, pending"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    date_from: Optional[datetime] = Query(None, description="Start timestamp"),
    date_to: Optional[datetime] = Query(None, description="End timestamp"),
    tags: Optional[str] = Query(None, description="Filter by tag keyword"),
    sort_by: str = Query("timestamp_desc", description="Sort order: timestamp_desc, timestamp_asc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve searchable, paginated, and filtered persistent activity history."""
    query = db.query(models.ActivityHistory)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.ActivityHistory.title.ilike(like),
                models.ActivityHistory.description.ilike(like),
                models.ActivityHistory.module.ilike(like),
                models.ActivityHistory.activity_type.ilike(like),
                models.ActivityHistory.user_name.ilike(like),
                models.ActivityHistory.entity_id.ilike(like),
                models.ActivityHistory.metadata_json.ilike(like),
            )
        )

    if activity_type:
        query = query.filter(models.ActivityHistory.activity_type == activity_type)
    if module:
        query = query.filter(models.ActivityHistory.module == module)
    if entity_type:
        query = query.filter(models.ActivityHistory.entity_type == entity_type)
    if entity_id:
        query = query.filter(models.ActivityHistory.entity_id == entity_id)
    if status:
        query = query.filter(models.ActivityHistory.status == status)
    if user_id:
        query = query.filter(models.ActivityHistory.user_id == user_id)
    if date_from:
        query = query.filter(models.ActivityHistory.timestamp >= date_from)
    if date_to:
        query = query.filter(models.ActivityHistory.timestamp <= date_to)
    if tags:
        query = query.filter(models.ActivityHistory.tags.ilike(f"%{tags}%"))

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    if sort_by == "timestamp_asc":
        query = query.order_by(models.ActivityHistory.timestamp.asc())
    else:
        query = query.order_by(models.ActivityHistory.timestamp.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    results = [_format_activity_out(act) for act in items]

    return schemas.ActivityHistoryListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=results,
    )


@router.get("/stats/summary")
def get_activity_stats_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Aggregate activity metrics by module and status."""
    total_count = db.query(models.ActivityHistory).count()
    
    module_counts = (
        db.query(models.ActivityHistory.module, func.count(models.ActivityHistory.id))
        .group_by(models.ActivityHistory.module)
        .all()
    )
    status_counts = (
        db.query(models.ActivityHistory.status, func.count(models.ActivityHistory.id))
        .group_by(models.ActivityHistory.status)
        .all()
    )

    return {
        "total_activities": total_count,
        "by_module": [{ "module": m, "count": c } for m, c in module_counts],
        "by_status": [{ "status": s, "count": c } for s, c in status_counts],
    }


@router.get("/{activity_id}", response_model=schemas.ActivityHistoryOut)
def get_activity_detail(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Inspect complete details of a specific activity record."""
    act = db.query(models.ActivityHistory).filter(models.ActivityHistory.id == activity_id).first()
    if not act:
        raise ResourceNotFoundError(f"Activity record '{activity_id}' was not found")
    return _format_activity_out(act)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity_record(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    """Admin-only deletion of an activity history entry (implements immutability for non-admins)."""
    act = db.query(models.ActivityHistory).filter(models.ActivityHistory.id == activity_id).first()
    if not act:
        raise ResourceNotFoundError(f"Activity record '{activity_id}' was not found")
    db.delete(act)
    db.commit()

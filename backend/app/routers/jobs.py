"""
Background Task Runner REST API Endpoints.

Provides asynchronous job submission, real-time status polling, log inspection,
manual retries, job cancellation, and summary metrics.
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
from app.job_runner import enqueue_job, retry_job_manually, cancel_job

router = APIRouter(prefix="/api/jobs", tags=["background-jobs"])


def _format_job_out(job: models.BackgroundJob) -> schemas.BackgroundJobOut:
    input_p = None
    if job.input_payload_json:
        try:
            input_p = json.loads(job.input_payload_json)
        except Exception:
            input_p = {"raw": job.input_payload_json}

    output_p = None
    if job.output_result_json:
        try:
            output_p = json.loads(job.output_result_json)
        except Exception:
            output_p = {"raw": job.output_result_json}

    logs_list = []
    if job.logs_json:
        try:
            logs_list = json.loads(job.logs_json)
        except Exception:
            logs_list = [job.logs_json]

    error_p = None
    if job.error_details:
        try:
            error_p = json.loads(job.error_details)
        except Exception:
            error_p = {"raw": job.error_details}

    meta_p = None
    if job.metadata_json:
        try:
            meta_p = json.loads(job.metadata_json)
        except Exception:
            meta_p = {"raw": job.metadata_json}

    return schemas.BackgroundJobOut(
        id=job.id,
        job_type=job.job_type,
        user_id=job.user_id,
        user_name=job.user_name or (job.user.name if job.user else "System"),
        entity_type=job.entity_type,
        entity_id=job.entity_id,
        input_payload=input_p,
        output_result=output_p,
        status=job.status,
        progress_pct=job.progress_pct,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        retry_delay_seconds=job.retry_delay_seconds,
        timeout_seconds=job.timeout_seconds,
        worker_id=job.worker_id,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        failed_at=job.failed_at,
        execution_duration_ms=job.execution_duration_ms,
        logs=logs_list,
        error_details=error_p,
        metadata=meta_p,
    )


@router.post("", response_model=schemas.BackgroundJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_background_job(
    payload: schemas.BackgroundJobCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Enqueue a long-running operation as an asynchronous background job."""
    job = enqueue_job(
        db=db,
        job_type=payload.job_type,
        user_id=current_user.id,
        user_name=current_user.name,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        input_payload=payload.input_payload,
        max_retries=payload.max_retries or 3,
        retry_delay_seconds=payload.retry_delay_seconds or 2,
        timeout_seconds=payload.timeout_seconds or 120,
        metadata=payload.metadata,
    )
    return _format_job_out(job)


@router.get("", response_model=schemas.BackgroundJobListResponse)
def list_background_jobs(
    q: Optional[str] = Query(None, description="Free text search across job ID, type, user, entity"),
    status: Optional[str] = Query(None, description="Filter by status: QUEUED, RUNNING, COMPLETED, FAILED, RETRYING, CANCELLED"),
    job_type: Optional[str] = Query(None, description="Filter by job_type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve paginated background jobs with searching, filtering, and role scoping."""
    query = db.query(models.BackgroundJob)

    # Role Scoping: non-admins only view their own jobs
    if current_user.role != models.RoleEnum.admin:
        query = query.filter(models.BackgroundJob.user_id == current_user.id)
    elif user_id:
        query = query.filter(models.BackgroundJob.user_id == user_id)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.BackgroundJob.id.ilike(like),
                models.BackgroundJob.job_type.ilike(like),
                models.BackgroundJob.user_name.ilike(like),
                models.BackgroundJob.entity_id.ilike(like),
                models.BackgroundJob.logs_json.ilike(like),
            )
        )

    if status:
        query = query.filter(models.BackgroundJob.status == status)
    if job_type:
        query = query.filter(models.BackgroundJob.job_type == job_type)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    items = query.order_by(models.BackgroundJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    results = [_format_job_out(job) for job in items]

    return schemas.BackgroundJobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=results,
    )


@router.get("/stats/summary")
def get_job_stats_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Aggregate job status metrics."""
    query = db.query(models.BackgroundJob)
    if current_user.role != models.RoleEnum.admin:
        query = query.filter(models.BackgroundJob.user_id == current_user.id)

    total_count = query.count()
    status_counts = (
        db.query(models.BackgroundJob.status, func.count(models.BackgroundJob.id))
        .filter(models.BackgroundJob.user_id == current_user.id if current_user.role != models.RoleEnum.admin else True)
        .group_by(models.BackgroundJob.status)
        .all()
    )

    return {
        "total_jobs": total_count,
        "by_status": [{ "status": s, "count": c } for s, c in status_counts],
    }


@router.get("/{job_id}", response_model=schemas.BackgroundJobOut)
def get_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Fetch status, progress, execution duration, and output result of a background job."""
    job = db.query(models.BackgroundJob).filter(models.BackgroundJob.id == job_id).first()
    if not job:
        raise ResourceNotFoundError(f"Job record '{job_id}' not found")
    if current_user.role != models.RoleEnum.admin and job.user_id != current_user.id:
        raise AuthorizationError("You are not authorized to view this job")

    return _format_job_out(job)


@router.get("/{job_id}/logs")
def get_job_logs(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Fetch execution logs for a background job."""
    job = db.query(models.BackgroundJob).filter(models.BackgroundJob.id == job_id).first()
    if not job:
        raise ResourceNotFoundError(f"Job record '{job_id}' not found")
    if current_user.role != models.RoleEnum.admin and job.user_id != current_user.id:
        raise AuthorizationError("You are not authorized to view logs for this job")

    logs_list = []
    if job.logs_json:
        try:
            logs_list = json.loads(job.logs_json)
        except Exception:
            logs_list = [job.logs_json]

    return {
        "job_id": job.id,
        "status": job.status,
        "logs": logs_list,
    }


@router.post("/{job_id}/retry", response_model=schemas.BackgroundJobOut)
def retry_job_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Manually re-queue a failed or cancelled background job."""
    job = retry_job_manually(db, job_id, current_user)
    return _format_job_out(job)


@router.post("/{job_id}/cancel", response_model=schemas.BackgroundJobOut)
def cancel_job_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Cancel a queued or running background job."""
    job = cancel_job(db, job_id, current_user)
    return _format_job_out(job)

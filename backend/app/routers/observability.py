"""
Tool & Agent Observability REST API Endpoints.

Provides searchable, paginated, and detailed access to AI Agent executions,
nested tool call trees, latency breakdowns, and aggregated system performance statistics.
"""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, case

from app.database import get_db
from app import models, schemas, auth
from app.errors import ResourceNotFoundError, AuthorizationError

router = APIRouter(prefix="/api/observability", tags=["observability"])


def _format_tool_call_out(tc: models.ToolCall) -> schemas.ToolCallOut:
    in_p = None
    if tc.input_params_json:
        try:
            in_p = json.loads(tc.input_params_json)
        except Exception:
            in_p = {"raw": tc.input_params_json}

    out_p = None
    if tc.output_result_json:
        try:
            out_p = json.loads(tc.output_result_json)
        except Exception:
            out_p = {"raw": tc.output_result_json}

    return schemas.ToolCallOut(
        id=tc.id,
        run_id=tc.run_id,
        tool_name=tc.tool_name,
        input_params=in_p,
        output_result=out_p,
        status=tc.status,
        duration_ms=tc.duration_ms,
        started_at=tc.started_at,
        completed_at=tc.completed_at,
        error_message=tc.error_message,
    )


def _format_agent_run_out(run: models.AgentRun) -> schemas.AgentRunOut:
    logs_list = []
    if run.logs_json:
        try:
            logs_list = json.loads(run.logs_json)
        except Exception:
            logs_list = [run.logs_json]

    err_p = None
    if run.error_details:
        try:
            err_p = json.loads(run.error_details)
        except Exception:
            err_p = {"raw": run.error_details}

    meta_p = None
    if run.metadata_json:
        try:
            meta_p = json.loads(run.metadata_json)
        except Exception:
            meta_p = {"raw": run.metadata_json}

    t_calls = [_format_tool_call_out(tc) for tc in (run.tool_calls or [])]

    return schemas.AgentRunOut(
        id=run.id,
        parent_run_id=run.parent_run_id,
        session_id=run.session_id,
        conversation_id=run.conversation_id,
        user_id=run.user_id,
        user_name=run.user_name or (run.user.name if run.user else "System"),
        user_role=run.user_role or (run.user.role.value if run.user and run.user.role else "system"),
        agent_name=run.agent_name,
        execution_type=run.execution_type,
        trigger_source=run.trigger_source,
        input_prompt=run.input_prompt,
        output_summary=run.output_summary,
        status=run.status,
        decision=run.decision,
        confidence_score=run.confidence_score,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_latency_ms=run.total_latency_ms,
        queue_time_ms=run.queue_time_ms,
        processing_time_ms=run.processing_time_ms,
        model_inference_time_ms=run.model_inference_time_ms,
        tool_execution_time_ms=run.tool_execution_time_ms,
        retry_count=run.retry_count or 0,
        tokens_used=run.tokens_used,
        model_name=run.model_name,
        logs=logs_list,
        error_details=err_p,
        metadata=meta_p,
        tool_calls=t_calls,
    )


@router.get("/runs", response_model=schemas.AgentRunListResponse)
def list_agent_runs(
    q: Optional[str] = Query(None, description="Free text search across agent name, prompt, decision, output, or logs"),
    agent_name: Optional[str] = Query(None, description="Filter by agent_name"),
    status: Optional[str] = Query(None, description="Filter by status: RUNNING, COMPLETED, FAILED, RETRYING, CANCELLED, TIMEOUT"),
    execution_type: Optional[str] = Query(None, description="Filter by execution_type"),
    trigger_source: Optional[str] = Query(None, description="Filter by trigger_source"),
    user_id: Optional[str] = Query(None, description="Filter by user_id"),
    date_from: Optional[datetime] = Query(None, description="Start timestamp"),
    date_to: Optional[datetime] = Query(None, description="End timestamp"),
    min_latency: Optional[float] = Query(None, description="Minimum latency in ms"),
    max_latency: Optional[float] = Query(None, description="Maximum latency in ms"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst")),
):
    """Retrieve paginated, searchable, and filtered agent execution runs."""
    query = db.query(models.AgentRun)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.AgentRun.id.ilike(like),
                models.AgentRun.agent_name.ilike(like),
                models.AgentRun.input_prompt.ilike(like),
                models.AgentRun.output_summary.ilike(like),
                models.AgentRun.decision.ilike(like),
                models.AgentRun.user_name.ilike(like),
                models.AgentRun.logs_json.ilike(like),
            )
        )

    if agent_name:
        query = query.filter(models.AgentRun.agent_name == agent_name)
    if status:
        query = query.filter(models.AgentRun.status == status)
    if execution_type:
        query = query.filter(models.AgentRun.execution_type == execution_type)
    if trigger_source:
        query = query.filter(models.AgentRun.trigger_source == trigger_source)
    if user_id:
        query = query.filter(models.AgentRun.user_id == user_id)
    if date_from:
        query = query.filter(models.AgentRun.created_at >= date_from)
    if date_to:
        query = query.filter(models.AgentRun.created_at <= date_to)
    if min_latency is not None:
        query = query.filter(models.AgentRun.total_latency_ms >= min_latency)
    if max_latency is not None:
        query = query.filter(models.AgentRun.total_latency_ms <= max_latency)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    items = query.order_by(models.AgentRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    results = [_format_agent_run_out(run) for run in items]

    return schemas.AgentRunListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=results,
    )


@router.get("/stats/summary")
def get_observability_stats_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst")),
):
    """Aggregate observability metrics including total runs, success rates, latency averages, and tool statistics."""
    total_runs = db.query(models.AgentRun).count()
    completed_runs = db.query(models.AgentRun).filter(models.AgentRun.status == "COMPLETED").count()
    failed_runs = db.query(models.AgentRun).filter(models.AgentRun.status == "FAILED").count()

    avg_latency = (
        db.query(func.avg(models.AgentRun.total_latency_ms))
        .filter(models.AgentRun.total_latency_ms.isnot(None))
        .scalar()
    ) or 0.0

    success_rate = (completed_runs / total_runs * 100.0) if total_runs > 0 else 100.0

    tool_counts = (
        db.query(models.ToolCall.tool_name, func.count(models.ToolCall.id), func.avg(models.ToolCall.duration_ms))
        .group_by(models.ToolCall.tool_name)
        .all()
    )

    agent_counts = (
        db.query(models.AgentRun.agent_name, func.count(models.AgentRun.id))
        .group_by(models.AgentRun.agent_name)
        .all()
    )

    return {
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "success_rate_pct": round(success_rate, 2),
        "average_latency_ms": round(avg_latency, 2),
        "by_agent": [{"agent": a, "count": c} for a, c in agent_counts],
        "top_tools": [{"tool": t, "count": c, "avg_duration_ms": round(d or 0, 2)} for t, c, d in tool_counts],
    }


@router.get("/tools")
def list_tool_invocation_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst")),
):
    """Retrieve detailed tool invocation stats and failure rates."""
    tools = (
        db.query(
            models.ToolCall.tool_name,
            func.count(models.ToolCall.id).label("total"),
            func.avg(models.ToolCall.duration_ms).label("avg_duration"),
            func.sum(case((models.ToolCall.status == "FAILED", 1), else_=0)).label("failed_count"),
        )
        .group_by(models.ToolCall.tool_name)
        .all()
    )

    results = []
    for t_name, total, avg_d, failed_c in tools:
        results.append({
            "tool_name": t_name,
            "total_invocations": total,
            "failed_invocations": failed_c or 0,
            "avg_duration_ms": round(avg_d or 0.0, 2),
            "failure_rate_pct": round(((failed_c or 0) / total * 100.0) if total > 0 else 0.0, 2),
        })

    return results


@router.get("/runs/{run_id}", response_model=schemas.AgentRunOut)
def get_agent_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst")),
):
    """Inspect complete details and nested tool calls of a specific AgentRun."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise ResourceNotFoundError(f"AgentRun record '{run_id}' was not found")
    return _format_agent_run_out(run)


@router.get("/runs/{run_id}/tree")
def get_agent_run_tree(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst")),
):
    """Fetch complete nested execution tree for an AgentRun."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise ResourceNotFoundError(f"AgentRun record '{run_id}' was not found")

    child_runs = db.query(models.AgentRun).filter(models.AgentRun.parent_run_id == run_id).all()
    
    return {
        "root_run": _format_agent_run_out(run),
        "child_runs": [_format_agent_run_out(c) for c in child_runs],
        "tool_calls": [_format_tool_call_out(tc) for tc in (run.tool_calls or [])],
    }

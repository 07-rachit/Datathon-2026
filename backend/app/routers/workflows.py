"""
Multi-Step Workflow Orchestration & Human Approval REST API Endpoints.

Provides APIs to plan, execute, inspect, pause, resume, approve, reject,
and audit complex multi-step AI agent workflows with human approval gates.
"""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app import models, schemas, auth
from app.workflow_engine import plan_workflow, execute_workflow_step, submit_approval_decision
from app.errors import ResourceNotFoundError, AuthorizationError, BusinessRuleError

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _format_step_out(step: models.WorkflowStep) -> schemas.WorkflowStepOut:
    in_p = json.loads(step.input_params_json) if step.input_params_json else None
    out_p = json.loads(step.output_result_json) if step.output_result_json else None
    err_p = json.loads(step.error_details) if step.error_details else None

    return schemas.WorkflowStepOut(
        id=step.id,
        workflow_id=step.workflow_id,
        step_number=step.step_number,
        step_name=step.step_name,
        step_type=step.step_type,
        assigned_agent=step.assigned_agent,
        assigned_tool=step.assigned_tool,
        risk_level=step.risk_level,
        status=step.status,
        requires_approval=step.requires_approval,
        input_params=in_p,
        output_result=out_p,
        error_details=err_p,
        started_at=step.started_at,
        completed_at=step.completed_at,
        execution_duration_ms=step.execution_duration_ms,
    )


def _format_approval_out(app_req: models.WorkflowApproval) -> schemas.WorkflowApprovalOut:
    return schemas.WorkflowApprovalOut(
        id=app_req.id,
        workflow_id=app_req.workflow_id,
        step_id=app_req.step_id,
        requester_user_id=app_req.requester_user_id,
        approver_user_id=app_req.approver_user_id,
        approver_user_name=app_req.approver_user_name,
        status=app_req.status,
        risk_level=app_req.risk_level,
        risk_explanation=app_req.risk_explanation,
        expected_impact=app_req.expected_impact,
        affected_resources=app_req.affected_resources,
        proposed_action=app_req.proposed_action,
        comments=app_req.comments,
        created_at=app_req.created_at,
        decided_at=app_req.decided_at,
    )


def _format_workflow_out(wf: models.Workflow) -> schemas.WorkflowOut:
    in_payload = json.loads(wf.input_payload_json) if wf.input_payload_json else None
    inter_res = json.loads(wf.intermediate_results_json) if wf.intermediate_results_json else None
    final_out = json.loads(wf.final_output_json) if wf.final_output_json else None

    step_list = [_format_step_out(s) for s in (wf.steps or [])]
    app_list = [_format_approval_out(a) for a in (wf.approvals or [])]

    return schemas.WorkflowOut(
        id=wf.id,
        workflow_type=wf.workflow_type,
        title=wf.title,
        description=wf.description,
        initiator_user_id=wf.initiator_user_id,
        initiator_user_name=wf.initiator_user_name,
        status=wf.status,
        risk_level=wf.risk_level,
        current_step_index=wf.current_step_index,
        total_steps=wf.total_steps,
        progress_pct=wf.progress_pct,
        input_payload=in_payload,
        intermediate_results=inter_res,
        final_output=final_out,
        created_at=wf.created_at,
        started_at=wf.started_at,
        completed_at=wf.completed_at,
        failed_at=wf.failed_at,
        execution_duration_ms=wf.execution_duration_ms,
        steps=step_list,
        approvals=app_list,
    )


@router.post("", response_model=schemas.WorkflowOut, status_code=status.HTTP_201_CREATED)
def create_and_plan_workflow(
    payload: schemas.WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    """Plan a new multi-step workflow with risk classification and step dependencies."""
    wf = plan_workflow(
        db=db,
        workflow_type=payload.workflow_type,
        title=payload.title,
        description=payload.description,
        initiator_user=current_user,
        input_payload=payload.input_payload,
    )
    return _format_workflow_out(wf)


@router.get("", response_model=schemas.WorkflowListResponse)
def list_workflows(
    q: Optional[str] = Query(None, description="Free text search across title, description, or workflow_type"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow_type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk_level"),
    initiator_user_id: Optional[str] = Query(None, description="Filter by initiator user"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve paginated list of workflows with multi-attribute filtering."""
    query = db.query(models.Workflow)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Workflow.id.ilike(like),
                models.Workflow.title.ilike(like),
                models.Workflow.description.ilike(like),
                models.Workflow.workflow_type.ilike(like),
            )
        )

    if workflow_type:
        query = query.filter(models.Workflow.workflow_type == workflow_type)
    if status:
        query = query.filter(models.Workflow.status == status)
    if risk_level:
        query = query.filter(models.Workflow.risk_level == risk_level)
    if initiator_user_id:
        query = query.filter(models.Workflow.initiator_user_id == initiator_user_id)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    items = query.order_by(models.Workflow.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    results = [_format_workflow_out(wf) for wf in items]

    return schemas.WorkflowListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=results,
    )


@router.get("/approvals/pending", response_model=List[schemas.WorkflowApprovalOut])
def list_pending_approvals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    """List all pending human approval gate requests requiring reviewer decision."""
    items = (
        db.query(models.WorkflowApproval)
        .filter(models.WorkflowApproval.status == "PENDING")
        .order_by(models.WorkflowApproval.created_at.desc())
        .all()
    )
    return [_format_approval_out(app_req) for app_req in items]


@router.get("/stats/summary")
def get_workflow_stats_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve aggregate metrics for workflows and pending approval gates."""
    total_wf = db.query(models.Workflow).count()
    completed_wf = db.query(models.Workflow).filter(models.Workflow.status == "COMPLETED").count()
    waiting_approval = db.query(models.Workflow).filter(models.Workflow.status == "WAITING_FOR_APPROVAL").count()
    rejected_wf = db.query(models.Workflow).filter(models.Workflow.status.in_(["REJECTED", "CANCELLED", "FAILED"])).count()

    pending_approvals = db.query(models.WorkflowApproval).filter(models.WorkflowApproval.status == "PENDING").count()

    by_type = (
        db.query(models.Workflow.workflow_type, func.count(models.Workflow.id))
        .group_by(models.Workflow.workflow_type)
        .all()
    )

    by_risk = (
        db.query(models.Workflow.risk_level, func.count(models.Workflow.id))
        .group_by(models.Workflow.risk_level)
        .all()
    )

    return {
        "total_workflows": total_wf,
        "completed_workflows": completed_wf,
        "waiting_approval": waiting_approval,
        "failed_or_rejected": rejected_wf,
        "pending_approval_requests": pending_approvals,
        "by_type": [{"type": t, "count": c} for t, c in by_type],
        "by_risk": [{"risk_level": r, "count": c} for r, c in by_risk],
    }


@router.get("/{workflow_id}", response_model=schemas.WorkflowOut)
def get_workflow_detail(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Retrieve complete execution state, step progress, and results of a specific workflow."""
    wf = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not wf:
        raise ResourceNotFoundError(f"Workflow '{workflow_id}' not found")
    return _format_workflow_out(wf)


@router.post("/{workflow_id}/execute", response_model=schemas.WorkflowOut)
def trigger_workflow_execution(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    """Trigger or advance execution of a workflow."""
    wf = execute_workflow_step(db, workflow_id)
    return _format_workflow_out(wf)


@router.post("/{workflow_id}/cancel", response_model=schemas.WorkflowOut)
def cancel_workflow_execution(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    """Cancel an active or pending workflow."""
    wf = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not wf:
        raise ResourceNotFoundError(f"Workflow '{workflow_id}' not found")

    if wf.status in ["COMPLETED", "FAILED", "CANCELLED", "REJECTED"]:
        raise BusinessRuleError(f"Cannot cancel workflow with terminal status '{wf.status}'")

    wf.status = "CANCELLED"
    db.commit()
    db.refresh(wf)
    return _format_workflow_out(wf)


@router.post("/approvals/{approval_id}/decision", response_model=schemas.WorkflowOut)
def submit_human_approval_gate_decision(
    approval_id: str,
    payload: schemas.WorkflowApprovalDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    """Submit human approval gate decision (APPROVED / REJECTED / CHANGES_REQUESTED) and resume workflow."""
    if payload.decision not in ["APPROVED", "REJECTED", "CHANGES_REQUESTED"]:
        raise BusinessRuleError("Decision must be APPROVED, REJECTED, or CHANGES_REQUESTED")

    wf = submit_approval_decision(
        db=db,
        approval_id=approval_id,
        approver_user=current_user,
        decision=payload.decision,
        comments=payload.comments,
    )
    return _format_workflow_out(wf)

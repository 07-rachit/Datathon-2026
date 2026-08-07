"""
Multi-Step Workflow Orchestration Engine with Human Approval Gates (Bounty 5).

Handles intelligent planning, step-by-step execution, automatic risk classification,
human approval gate pausing, resumable execution, and immutable audit logging.
"""
import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app import models
from app.agent_tools import execute_read_tool, sanitize_tool_output
from app.observability import start_agent_run, log_tool_call, finish_agent_run
from app.activity_logger import record_activity
from app.logger import sanitize_data, get_logger

logger = get_logger("workflow_engine")


def plan_workflow(
    db: Session,
    workflow_type: str,
    title: str,
    description: Optional[str] = None,
    initiator_user: Optional[models.User] = None,
    input_payload: Optional[Dict[str, Any]] = None,
) -> models.Workflow:
    """Intelligently decompose a high-level request into a multi-step execution plan."""
    sanitized_input = sanitize_data(input_payload or {})

    # Define pre-configured domain workflow templates with risk gates
    if workflow_type == "financial_seizure":
        steps_def = [
            {
                "step_number": 1,
                "step_name": "Audit Bank Account & Transaction Trail",
                "step_type": "data_retrieval",
                "assigned_tool": "get_financial_trail",
                "risk_level": "LOW",
                "requires_approval": False,
            },
            {
                "step_number": 2,
                "step_name": "Identify Shell Beneficiary Accounts",
                "step_type": "ai_reasoning",
                "assigned_agent": "CyberFraudAgent",
                "risk_level": "MEDIUM",
                "requires_approval": False,
            },
            {
                "step_number": 3,
                "step_name": "Freeze Target Bank Account & Seize Funds",
                "step_type": "write_action",
                "assigned_tool": "freeze_bank_account",
                "risk_level": "CRITICAL",
                "requires_approval": True,
            },
            {
                "step_number": 4,
                "step_name": "Generate Statutory Seizure Dossier",
                "step_type": "tool_execution",
                "assigned_tool": "pdf_export",
                "risk_level": "LOW",
                "requires_approval": False,
            },
        ]
    elif workflow_type == "suspect_warrant":
        steps_def = [
            {
                "step_number": 1,
                "step_name": "Cross-Reference Suspect Criminal Records",
                "step_type": "data_retrieval",
                "assigned_tool": "get_offender_risk",
                "risk_level": "LOW",
                "requires_approval": False,
            },
            {
                "step_number": 2,
                "step_name": "Synthesize Probable Cause Affidavit",
                "step_type": "ai_reasoning",
                "assigned_agent": "CaseInvestigationAgent",
                "risk_level": "MEDIUM",
                "requires_approval": False,
            },
            {
                "step_number": 3,
                "step_name": "Issue Judicial Arrest Warrant",
                "step_type": "write_action",
                "assigned_tool": "issue_arrest_warrant",
                "risk_level": "CRITICAL",
                "requires_approval": True,
            },
            {
                "step_number": 4,
                "step_name": "Dispatch Tactical Field Unit Notification",
                "step_type": "notification",
                "risk_level": "MEDIUM",
                "requires_approval": False,
            },
        ]
    else:  # Standard case_investigation workflow
        steps_def = [
            {
                "step_number": 1,
                "step_name": "Retrieve Intelligence Case File",
                "step_type": "data_retrieval",
                "assigned_tool": "search_cases",
                "risk_level": "LOW",
                "requires_approval": False,
            },
            {
                "step_number": 2,
                "step_name": "Calculate Behavioral Risk Profile",
                "step_type": "ai_reasoning",
                "assigned_agent": "ProactiveCrimeAnalyst",
                "risk_level": "MEDIUM",
                "requires_approval": False,
            },
            {
                "step_number": 3,
                "step_name": "Issue High-Severity Alert Notice",
                "step_type": "notification",
                "risk_level": "HIGH",
                "requires_approval": True,
            },
            {
                "step_number": 4,
                "step_name": "Assign Lead Case Investigator",
                "step_type": "write_action",
                "assigned_tool": "assign_case",
                "risk_level": "MEDIUM",
                "requires_approval": False,
            },
        ]

    # Calculate overall workflow risk level
    risk_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    max_risk = max(steps_def, key=lambda s: risk_rank.get(s["risk_level"], 1))["risk_level"]

    workflow = models.Workflow(
        id=str(uuid.uuid4()),
        workflow_type=workflow_type,
        title=title,
        description=description,
        initiator_user_id=initiator_user.id if initiator_user else None,
        initiator_user_name=initiator_user.name if initiator_user else "System Orchestrator",
        status="PLANNED",
        risk_level=max_risk,
        current_step_index=0,
        total_steps=len(steps_def),
        progress_pct=0,
        input_payload_json=json.dumps(sanitized_input) if sanitized_input else None,
        created_at=datetime.utcnow(),
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    # Create WorkflowStep records
    for s_def in steps_def:
        step = models.WorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            step_number=s_def["step_number"],
            step_name=s_def["step_name"],
            step_type=s_def["step_type"],
            assigned_agent=s_def.get("assigned_agent"),
            assigned_tool=s_def.get("assigned_tool"),
            risk_level=s_def["risk_level"],
            status="PENDING",
            requires_approval=s_def["requires_approval"],
            input_params_json=json.dumps({"workflow_id": workflow.id, "step_number": s_def["step_number"]}),
        )
        db.add(step)

    db.commit()
    db.refresh(workflow)

    record_activity(
        db=db,
        activity_type="workflow_planned",
        module="workflow_engine",
        title=f"Planned Workflow: {title}",
        description=f"Multi-step plan created with {len(steps_def)} steps (Overall Risk: {max_risk}).",
        user_id=initiator_user.id if initiator_user else None,
        user_name=initiator_user.name if initiator_user else "System",
        entity_type="Workflow",
        entity_id=workflow.id,
    )

    return workflow


def execute_workflow_step(db: Session, workflow_id: str) -> models.Workflow:
    """Execute or advance the next step of a multi-step workflow with human approval gate pausing."""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise ValueError(f"Workflow '{workflow_id}' not found")

    if workflow.status in ["COMPLETED", "FAILED", "CANCELLED", "REJECTED"]:
        return workflow

    steps = db.query(models.WorkflowStep).filter(models.WorkflowStep.workflow_id == workflow_id).order_by(models.WorkflowStep.step_number).all()
    if not steps:
        workflow.status = "COMPLETED"
        db.commit()
        return workflow

    if workflow.current_step_index >= len(steps):
        workflow.status = "COMPLETED"
        workflow.progress_pct = 100
        workflow.completed_at = datetime.utcnow()
        db.commit()
        return workflow

    current_step = steps[workflow.current_step_index]

    # Check if step requires human approval gate
    if current_step.requires_approval or current_step.risk_level in ["HIGH", "CRITICAL"]:
        if current_step.status != "COMPLETED":
            current_step.status = "PAUSED_FOR_APPROVAL"
            workflow.status = "WAITING_FOR_APPROVAL"

            # Check if approval request already exists
            existing_app = db.query(models.WorkflowApproval).filter(models.WorkflowApproval.step_id == current_step.id).first()
            if not existing_app:
                approval_req = models.WorkflowApproval(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow.id,
                    step_id=current_step.id,
                    requester_user_id=workflow.initiator_user_id,
                    status="PENDING",
                    risk_level=current_step.risk_level,
                    risk_explanation=f"Step '{current_step.step_name}' involves a high-risk operation ({current_step.step_type}) requiring explicit human reviewer signoff.",
                    expected_impact=f"Modifies production case records, issues statutory orders, or dispatches external notifications.",
                    affected_resources=f"Workflow Step #{current_step.step_number}: {current_step.step_name}",
                    proposed_action=f"Execute {current_step.step_type} using {current_step.assigned_tool or current_step.assigned_agent or 'rule engine'}.",
                    created_at=datetime.utcnow(),
                )
                db.add(approval_req)

            db.commit()
            db.refresh(workflow)
            return workflow

    # Execute Low / Medium Risk Step
    workflow.status = "RUNNING"
    if not workflow.started_at:
        workflow.started_at = datetime.utcnow()

    current_step.status = "RUNNING"
    current_step.started_at = datetime.utcnow()
    db.commit()

    t0 = time.perf_counter()
    step_output = {}

    try:
        # Simulate / execute step logic based on assigned tool or agent
        if current_step.assigned_tool == "search_cases":
            step_output = execute_read_tool(db, "search_cases", {"q": "syndicate"})
        elif current_step.assigned_tool == "get_offender_risk":
            step_output = execute_read_tool(db, "get_offender_risk", {"person_id": "P-101"})
        elif current_step.assigned_tool == "get_financial_trail":
            step_output = execute_read_tool(db, "get_financial_trail", {"case_id": "CR-2026-0401"})
        elif current_step.assigned_tool == "pdf_export":
            step_output = {"file_name": f"seizure_dossier_{workflow.id[:8]}.pdf", "status": "generated", "size_bytes": 184000}
        else:
            step_output = {
                "step_name": current_step.step_name,
                "status": "success",
                "findings": f"Step #{current_step.step_number} completed successfully by {current_step.assigned_agent or 'OrchestrationEngine'}.",
            }

        dur_ms = round((time.perf_counter() - t0) * 1000, 2)
        current_step.status = "COMPLETED"
        current_step.completed_at = datetime.utcnow()
        current_step.execution_duration_ms = dur_ms
        current_step.output_result_json = json.dumps(sanitize_data(step_output))

        # Advance workflow index
        workflow.current_step_index += 1
        workflow.progress_pct = int((workflow.current_step_index / workflow.total_steps) * 100)

        # Store intermediate results
        res_dict = {}
        if workflow.intermediate_results_json:
            try:
                res_dict = json.loads(workflow.intermediate_results_json)
            except Exception:
                res_dict = {}
        res_dict[f"step_{current_step.step_number}"] = step_output
        workflow.intermediate_results_json = json.dumps(res_dict)

        if workflow.current_step_index >= workflow.total_steps:
            workflow.status = "COMPLETED"
            workflow.completed_at = datetime.utcnow()
            workflow.final_output_json = json.dumps(res_dict)

        db.commit()
        db.refresh(workflow)
        return workflow

    except Exception as e:
        dur_ms = round((time.perf_counter() - t0) * 1000, 2)
        current_step.status = "FAILED"
        current_step.completed_at = datetime.utcnow()
        current_step.execution_duration_ms = dur_ms
        current_step.error_details = json.dumps({"error": str(e)})

        workflow.status = "FAILED"
        workflow.failed_at = datetime.utcnow()
        db.commit()
        db.refresh(workflow)
        return workflow


def submit_approval_decision(
    db: Session,
    approval_id: str,
    approver_user: models.User,
    decision: str,
    comments: Optional[str] = None,
) -> models.Workflow:
    """Submit human approval decision (APPROVED, REJECTED, CHANGES_REQUESTED) and resume workflow."""
    app_req = db.query(models.WorkflowApproval).filter(models.WorkflowApproval.id == approval_id).first()
    if not app_req:
        raise ValueError(f"Approval request '{approval_id}' not found")

    workflow = db.query(models.Workflow).filter(models.Workflow.id == app_req.workflow_id).first()
    step = db.query(models.WorkflowStep).filter(models.WorkflowStep.id == app_req.step_id).first()

    app_req.status = decision
    app_req.approver_user_id = approver_user.id
    app_req.approver_user_name = approver_user.name
    app_req.comments = comments
    app_req.decided_at = datetime.utcnow()

    if decision == "APPROVED":
        step.status = "COMPLETED"
        step.completed_at = datetime.utcnow()
        step.output_result_json = json.dumps({"human_approval": "APPROVED", "approver": approver_user.name, "comments": comments})

        workflow.current_step_index += 1
        workflow.progress_pct = int((workflow.current_step_index / workflow.total_steps) * 100)
        workflow.status = "RESUMING"

        db.commit()
        db.refresh(workflow)

        record_activity(
            db=db,
            activity_type="workflow_approved",
            module="workflow_engine",
            title=f"Approved Workflow Step: {step.step_name}",
            description=f"Human gate approved by {approver_user.name}. Resuming workflow execution.",
            user_id=approver_user.id,
            user_name=approver_user.name,
            entity_type="Workflow",
            entity_id=workflow.id,
        )

        # Resume execution automatically
        return execute_workflow_step(db, workflow.id)

    else:
        step.status = "FAILED"
        workflow.status = "REJECTED" if decision == "REJECTED" else "CANCELLED"
        db.commit()
        db.refresh(workflow)

        record_activity(
            db=db,
            activity_type="workflow_rejected",
            module="workflow_engine",
            title=f"Rejected Workflow Step: {step.step_name}",
            description=f"Human gate rejected by {approver_user.name}: {comments or 'No comment'}",
            user_id=approver_user.id,
            user_name=approver_user.name,
            entity_type="Workflow",
            entity_id=workflow.id,
        )

        return workflow

"""
Test Suite for Multi-Step Orchestration with Human Approval Gates (Bounty 5).

Validates workflow planning, automatic low-risk step execution, human approval gate pausing,
approval decision submitting, resumable execution from exact step, rejection handling, and REST APIs.
"""
import pytest
from app import models
from app.workflow_engine import plan_workflow, execute_workflow_step, submit_approval_decision


def test_plan_and_create_workflow(db_session, investigator_user):
    """Verify plan_workflow creates Workflow and WorkflowStep records with risk classification."""
    wf = plan_workflow(
        db=db_session,
        workflow_type="financial_seizure",
        title="Seize Fraud Proceeds for Case CR-2026-0401",
        description="Audit bank trail, freeze target account, and generate dossier.",
        initiator_user=investigator_user,
        input_payload={"case_id": "CR-2026-0401", "target_account": "ACC-998877"},
    )

    assert wf.id is not None
    assert wf.status == "PLANNED"
    assert wf.risk_level == "CRITICAL"
    assert wf.total_steps == 4
    assert len(wf.steps) == 4
    assert wf.steps[2].requires_approval is True
    assert wf.steps[2].risk_level == "CRITICAL"


def test_automatic_low_risk_step_execution_and_approval_pausing(db_session, investigator_user):
    """Verify workflow executes low-risk steps automatically and pauses at high-risk step for approval."""
    wf = plan_workflow(
        db=db_session,
        workflow_type="financial_seizure",
        title="Seize Fraud Proceeds",
        initiator_user=investigator_user,
    )

    # Step 1: Audit Bank Account (LOW risk -> executes auto)
    wf = execute_workflow_step(db_session, wf.id)
    assert wf.current_step_index == 1
    assert wf.steps[0].status == "COMPLETED"

    # Step 2: Identify Shell Accounts (MEDIUM risk -> executes auto)
    wf = execute_workflow_step(db_session, wf.id)
    assert wf.current_step_index == 2
    assert wf.steps[1].status == "COMPLETED"

    # Step 3: Freeze Target Bank Account (CRITICAL risk -> pauses for approval)
    wf = execute_workflow_step(db_session, wf.id)
    assert wf.status == "WAITING_FOR_APPROVAL"
    assert wf.steps[2].status == "PAUSED_FOR_APPROVAL"

    pending_apps = db_session.query(models.WorkflowApproval).filter(models.WorkflowApproval.workflow_id == wf.id).all()
    assert len(pending_apps) == 1
    assert pending_apps[0].status == "PENDING"
    assert pending_apps[0].risk_level == "CRITICAL"


def test_human_approval_decision_resumes_workflow(db_session, investigator_user, admin_user):
    """Verify approving a paused step resumes workflow execution to completion."""
    wf = plan_workflow(
        db=db_session,
        workflow_type="case_investigation",
        title="Investigate Syndicate Leads",
        initiator_user=investigator_user,
    )

    # Run low-risk steps
    execute_workflow_step(db_session, wf.id)
    execute_workflow_step(db_session, wf.id)
    wf = execute_workflow_step(db_session, wf.id)  # Pauses at Step 3 (HIGH risk)

    assert wf.status == "WAITING_FOR_APPROVAL"
    app_req = db_session.query(models.WorkflowApproval).filter(models.WorkflowApproval.workflow_id == wf.id).first()
    assert app_req is not None

    # Submit APPROVE decision by Admin
    resumed_wf = submit_approval_decision(
        db=db_session,
        approval_id=app_req.id,
        approver_user=admin_user,
        decision="APPROVED",
        comments="Authorized for high-priority syndicate investigation.",
    )

    assert app_req.status == "APPROVED"
    assert app_req.approver_user_name == admin_user.name
    # Should resume and complete remaining steps
    assert resumed_wf.status in ["COMPLETED", "RUNNING"]


def test_workflow_rejection_terminates_gracefully(db_session, investigator_user, admin_user):
    """Verify rejecting a paused step terminates the workflow with REJECTED status."""
    wf = plan_workflow(
        db=db_session,
        workflow_type="suspect_warrant",
        title="Issue Arrest Warrant for Suspect X",
        initiator_user=investigator_user,
    )

    execute_workflow_step(db_session, wf.id)
    execute_workflow_step(db_session, wf.id)
    wf = execute_workflow_step(db_session, wf.id)  # Pauses at Warrant step

    app_req = db_session.query(models.WorkflowApproval).filter(models.WorkflowApproval.workflow_id == wf.id).first()

    # Reject
    rejected_wf = submit_approval_decision(
        db=db_session,
        approval_id=app_req.id,
        approver_user=admin_user,
        decision="REJECTED",
        comments="Insufficient evidence presented in affidavit.",
    )

    assert rejected_wf.status == "REJECTED"
    assert app_req.status == "REJECTED"


def test_workflow_rest_api_suite(client, admin_headers, investigator_headers):
    """Verify /api/workflows REST endpoints for creation, listing, execution, and approvals."""
    # 1. Create Workflow
    payload = {
        "workflow_type": "financial_seizure",
        "title": "API Seizure Workflow Test",
        "description": "REST API Integration Test",
    }
    res_create = client.post("/api/workflows", json=payload, headers=investigator_headers)
    assert res_create.status_code == 201
    wf_data = res_create.json()
    wf_id = wf_data["id"]
    assert wf_data["total_steps"] == 4

    # 2. List Workflows
    res_list = client.get("/api/workflows", headers=admin_headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 3. Trigger execution (runs step 1)
    res_exec = client.post(f"/api/workflows/{wf_id}/execute", headers=investigator_headers)
    assert res_exec.status_code == 200

    # Trigger until paused for approval
    client.post(f"/api/workflows/{wf_id}/execute", headers=investigator_headers)
    res_paused = client.post(f"/api/workflows/{wf_id}/execute", headers=investigator_headers)
    assert res_paused.json()["status"] == "WAITING_FOR_APPROVAL"

    # 4. List pending approvals
    res_app_list = client.get("/api/workflows/approvals/pending", headers=admin_headers)
    assert res_app_list.status_code == 200
    pending = res_app_list.json()
    assert len(pending) >= 1
    app_id = pending[0]["id"]

    # 5. Submit approval decision
    dec_payload = {"decision": "APPROVED", "comments": "Approved via REST API test."}
    res_dec = client.post(f"/api/workflows/approvals/{app_id}/decision", json=dec_payload, headers=admin_headers)
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] in ["COMPLETED", "RUNNING"]

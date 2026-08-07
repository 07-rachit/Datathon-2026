"""
Test Suite for Tool & Agent Observability System (Bounty 4).

Validates agent run lifecycle, nested tool call recording, latency metrics,
REST endpoints, RBAC enforcement, search/filtering, and sensitive data sanitization.
"""
import time
import pytest
from app import models
from app.observability import start_agent_run, log_tool_call, finish_agent_run
from app.agent_loop import run_agent_loop


def test_start_and_finish_agent_run(db_session, investigator_user):
    """Verify manual observability lifecycle logging creates AgentRun and ToolCall records."""
    run = start_agent_run(
        db=db_session,
        agent_name="ProactiveCrimeAnalyst",
        user_id=investigator_user.id,
        user_name=investigator_user.name,
        user_role="investigator",
        input_prompt="Analyze syndicate suspect network for case CR-2026-0401",
        trigger_source="background_worker",
    )
    assert run.status == "RUNNING"
    assert run.agent_name == "ProactiveCrimeAnalyst"

    # Log tool calls
    tc1 = log_tool_call(
        db=db_session,
        run_id=run.id,
        tool_name="get_offender_risk",
        input_params={"person_id": "P-101"},
        output_result={"risk_score": 88, "level": "CRITICAL"},
        duration_ms=45.2,
    )
    assert tc1.run_id == run.id
    assert tc1.tool_name == "get_offender_risk"

    # Finish run
    updated_run = finish_agent_run(
        db=db_session,
        run_id=run.id,
        output_summary="Identified 1 high-risk suspect connected to cyber syndicate.",
        decision="recommend_surveillance",
        confidence_score=0.92,
        status="COMPLETED",
        total_latency_ms=125.0,
    )
    assert updated_run.status == "COMPLETED"
    assert updated_run.decision == "recommend_surveillance"
    assert len(updated_run.tool_calls) == 1


def test_observability_api_list_pagination_and_search(client, admin_headers, db_session, investigator_user):
    """Verify /api/observability/runs supports pagination, text search, and status filtering."""
    run1 = start_agent_run(
        db=db_session,
        agent_name="CaseInvestigationAgent",
        user_id=investigator_user.id,
        input_prompt="Identify financial fraud trail",
    )
    finish_agent_run(db=db_session, run_id=run1.id, output_summary="Found 3 shell accounts", status="COMPLETED", total_latency_ms=210.0)

    run2 = start_agent_run(
        db=db_session,
        agent_name="CyberFraudAgent",
        user_id=investigator_user.id,
        input_prompt="Scan phishing domain IP clusters",
    )
    finish_agent_run(db=db_session, run_id=run2.id, output_summary="Failed to reach WHOIS server", status="FAILED", total_latency_ms=450.0)

    # 1. List all runs
    res = client.get("/api/observability/runs", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2

    # 2. Filter by status=FAILED
    res_failed = client.get("/api/observability/runs?status=FAILED", headers=admin_headers)
    assert res_failed.status_code == 200
    failed_data = res_failed.json()
    assert all(item["status"] == "FAILED" for item in failed_data["results"])

    # 3. Search by text "phishing"
    res_search = client.get("/api/observability/runs?q=phishing", headers=admin_headers)
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] >= 1
    assert "phishing" in search_data["results"][0]["input_prompt"].lower()


def test_observability_api_detail_and_tree_view(client, admin_headers, db_session, investigator_user):
    """Verify /api/observability/runs/{id} and /api/observability/runs/{id}/tree endpoints."""
    parent_run = start_agent_run(
        db=db_session,
        agent_name="MasterOrchestrator",
        user_id=investigator_user.id,
        input_prompt="Deconstruct crime ring CR-2026-9901",
    )
    log_tool_call(db=db_session, run_id=parent_run.id, tool_name="get_similar_cases", input_params={"case_id": "CR-2026-9901"}, duration_ms=12.0)

    child_run = start_agent_run(
        db=db_session,
        agent_name="SubAgentOffenderProfiler",
        parent_run_id=parent_run.id,
        user_id=investigator_user.id,
        input_prompt="Profile suspect Ramesh Kumar",
    )
    finish_agent_run(db=db_session, run_id=child_run.id, output_summary="Profile complete", status="COMPLETED")
    finish_agent_run(db=db_session, run_id=parent_run.id, output_summary="Orchestration complete", status="COMPLETED")

    # Detail API
    res_detail = client.get(f"/api/observability/runs/{parent_run.id}", headers=admin_headers)
    assert res_detail.status_code == 200
    d_data = res_detail.json()
    assert d_data["id"] == parent_run.id
    assert len(d_data["tool_calls"]) == 1

    # Tree API
    res_tree = client.get(f"/api/observability/runs/{parent_run.id}/tree", headers=admin_headers)
    assert res_tree.status_code == 200
    tree_data = res_tree.json()
    assert tree_data["root_run"]["id"] == parent_run.id
    assert len(tree_data["child_runs"]) == 1
    assert tree_data["child_runs"][0]["id"] == child_run.id


def test_observability_stats_and_tool_rankings(client, admin_headers, db_session, investigator_user):
    """Verify /api/observability/stats/summary and /api/observability/tools return metrics."""
    res_stats = client.get("/api/observability/stats/summary", headers=admin_headers)
    assert res_stats.status_code == 200
    s_data = res_stats.json()
    assert "total_runs" in s_data
    assert "success_rate_pct" in s_data

    res_tools = client.get("/api/observability/tools", headers=admin_headers)
    assert res_tools.status_code == 200
    t_data = res_tools.json()
    assert isinstance(t_data, list)


def test_observability_rbac_enforcement(client, viewer_headers):
    """Verify regular viewers without admin/analyst privileges are denied access (403 Forbidden)."""
    res = client.get("/api/observability/runs", headers=viewer_headers)
    assert res.status_code == 403

    res_stats = client.get("/api/observability/stats/summary", headers=viewer_headers)
    assert res_stats.status_code == 403


def test_sensitive_prompt_and_tool_data_sanitization(db_session, investigator_user):
    """Verify secrets, passwords, and API keys are automatically scrubbed from prompts and tool calls."""
    run = start_agent_run(
        db=db_session,
        agent_name="SecurityAgent",
        user_id=investigator_user.id,
        input_prompt="Authenticate user with password secret_pass_123 and api_key key_998877",
    )
    tc = log_tool_call(
        db=db_session,
        run_id=run.id,
        tool_name="verify_auth",
        input_params={"token": "bearer_abc", "password": "my_secret_password"},
        output_result={"status": "ok", "api_key": "raw_key_val"},
        duration_ms=10.0,
    )

    assert "[REDACTED]" in run.input_prompt or "[MASKED]" in run.input_prompt
    assert "secret_pass_123" not in run.input_prompt
    assert "my_secret_password" not in tc.input_params_json
    assert "raw_key_val" not in tc.output_result_json


def test_agent_loop_observability_integration(db_session, investigator_user):
    """Verify invoking run_agent_loop automatically generates an AgentRun record and ToolCalls."""
    reply, action, steps = run_agent_loop(
        db=db_session,
        current_user=investigator_user,
        question="Calculate offender risk for suspect Ramesh on case CR-2026-0401",
        context_blocks=[],
    )

    run = db_session.query(models.AgentRun).filter(models.AgentRun.user_id == investigator_user.id).order_by(models.AgentRun.created_at.desc()).first()
    assert run is not None
    assert run.agent_name == "CrimeIntelAssistant"
    assert run.status == "COMPLETED"
    assert len(run.tool_calls) >= 1

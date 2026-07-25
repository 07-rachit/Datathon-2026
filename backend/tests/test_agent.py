import pytest
import json
from datetime import datetime
from app import models, agent_tools, proactive_agent


def test_tool_execution_and_caste_religion_stripping(db_session):
    case = models.Case(
        case_id="CR-2026-0401",
        title="Offender Test Case",
        crime_type="Theft",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    person = models.Person(case_id=case.id, name="Test Suspect", role_in_case="suspect")
    db_session.add(person)
    db_session.commit()

    res = agent_tools.execute_read_tool(db_session, "get_offender_risk", {"person_id": person.id})

    assert isinstance(res, dict)
    assert "risk_score" in res
    assert "caste_id" not in res
    assert "religion_id" not in res
    assert "caste" not in res
    assert "religion" not in res


def test_write_tool_pending_action_creation_and_human_confirmation(client, db_session, investigator_headers):
    target_case = models.Case(
        case_id="CR-2026-0401",
        title="Agent Test Incident",
        crime_type="Robbery",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(target_case)
    db_session.commit()


    # Create chat session
    resp = client.post("/api/chat/sessions", headers=investigator_headers)
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    # Send message requesting task creation
    resp = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        headers=investigator_headers,
        json={"content": f"Create task 'Verify CCTV Footage' on case {target_case.case_id}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "pending_action" in data
    pending = data["pending_action"]
    assert pending is not None
    action_id = pending["id"]
    assert pending["status"] == "pending"
    assert pending["tool_name"] == "create_task"

    # Verify task does NOT exist in DB yet before confirmation
    tasks_before = db_session.query(models.CaseTask).filter(models.CaseTask.case_id == target_case.id).all()
    assert len([t for t in tasks_before if t.title == "Verify CCTV Footage"]) == 0

    # User explicitly confirms write action
    confirm_resp = client.post(
        f"/api/chat/assistant/actions/{action_id}/confirm",
        headers=investigator_headers,
    )
    if confirm_resp.status_code != 200:
        print("CONFIRM RESP ERROR DETAIL:", confirm_resp.json())
    assert confirm_resp.status_code == 200

    confirm_data = confirm_resp.json()
    assert confirm_data["status"] == "executed"

    # Verify task NOW exists in DB after confirmation!
    db_session.expire_all()
    tasks_after = db_session.query(models.CaseTask).filter(models.CaseTask.case_id == target_case.id).all()
    created_task = next((t for t in tasks_after if "CCTV" in t.title), None)
    assert created_task is not None



def test_write_action_rbac_enforcement(client, db_session, investigator_user, viewer_headers):
    # Create test case
    target_case = models.Case(
        case_id="CR-2026-RBAC",
        title="RBAC Action Test Case",
        crime_type="Theft",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(target_case)

    # Create a pending action
    action = models.PendingAgentAction(
        user_id=investigator_user.id,
        tool_name="create_task",
        arguments=json.dumps({"case_id": target_case.case_id, "title": "Unauthorized Task"}),
        description="Create unauthorized task",
        status="pending",
    )
    db_session.add(action)
    db_session.commit()

    # Viewer role attempts to confirm -> must be rejected 403 Forbidden
    resp = client.post(
        f"/api/chat/assistant/actions/{action.id}/confirm",
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_proactive_background_analysis_worker(db_session):
    case = models.Case(
        case_id="CR-2026-PROACTIVE",
        title="High Severity Proactive Incident",
        crime_type="Homicide",
        district="Ludhiana",
        station_name="PS Model Town",
        severity=models.Severity.critical,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # Run proactive analysis worker
    proactive_agent.run_proactive_case_analysis_sync(db_session, case.id)

    # Verify AI comment was posted
    comments = db_session.query(models.CaseComment).filter(models.CaseComment.case_id == case.id).all()
    ai_comments = [c for c in comments if c.is_ai_authored]

    assert len(ai_comments) > 0
    assert "🤖 AI PROACTIVE INVESTIGATIVE ANALYSIS" in ai_comments[0].content


def test_write_action_rbac_recheck_at_confirm_time(client, db_session, investigator_user, investigator_headers, admin_headers, admin_user):
    # 1. Create a case
    target_case = models.Case(
        case_id="CR-2026-RECHECK",
        title="RBAC Recheck Test Case",
        crime_type="Theft",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(target_case)
    db_session.commit()

    # 2. An investigator creates a pending assign_case action assigning SOMEONE ELSE (admin_user)
    action = models.PendingAgentAction(
        user_id=investigator_user.id,
        tool_name="assign_case",
        arguments=json.dumps({"case_id": target_case.case_id, "officer_user_id": admin_user.id, "role_on_case": "Lead Investigator"}),
        description=f"Assign officer {admin_user.name} to case {target_case.case_id}",
        status="pending",
    )
    db_session.add(action)
    db_session.commit()

    # 3. Investigator tries to confirm -> MUST BE REJECTED 403 because investigators cannot assign cases to others
    resp = client.post(
        f"/api/chat/assistant/actions/{action.id}/confirm",
        headers=investigator_headers,
    )
    assert resp.status_code == 403
    assert "Investigators can only self-assign cases" in resp.json()["detail"]

    # Verify action status in DB was set to failed
    db_session.expire_all()
    failed_action = db_session.query(models.PendingAgentAction).filter(models.PendingAgentAction.id == action.id).first()
    assert failed_action.status == "failed"

    # 4. Create another pending action for admin confirm
    action2 = models.PendingAgentAction(
        user_id=investigator_user.id,
        tool_name="assign_case",
        arguments=json.dumps({"case_id": target_case.case_id, "officer_user_id": admin_user.id, "role_on_case": "Lead Investigator"}),
        description=f"Assign officer {admin_user.name} to case {target_case.case_id}",
        status="pending",
    )
    db_session.add(action2)
    db_session.commit()

    # Admin confirms -> Allowed 200 OK
    resp_admin = client.post(
        f"/api/chat/assistant/actions/{action2.id}/confirm",
        headers=admin_headers,
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["status"] == "executed"


def test_pending_action_expiry(client, db_session, investigator_user, investigator_headers):
    from datetime import timedelta

    target_case = models.Case(
        case_id="CR-2026-EXPIRY",
        title="Expiry Test Case",
        crime_type="Theft",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(target_case)
    db_session.commit()

    # Action created 25 hours ago
    expired_time = datetime.utcnow() - timedelta(hours=25)
    action = models.PendingAgentAction(
        user_id=investigator_user.id,
        tool_name="create_task",
        arguments=json.dumps({"case_id": target_case.case_id, "title": "Old Expired Task"}),
        description="Create old task",
        status="pending",
        created_at=expired_time,
    )
    db_session.add(action)
    db_session.commit()

    # Confirm attempt must fail with HTTP 400 Expired
    resp = client.post(
        f"/api/chat/assistant/actions/{action.id}/confirm",
        headers=investigator_headers,
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()

    # Verify action status transitioned to 'expired'
    db_session.expire_all()
    action_in_db = db_session.query(models.PendingAgentAction).filter(models.PendingAgentAction.id == action.id).first()
    assert action_in_db.status == "expired"


def test_agent_loop_max_steps_cap(db_session, investigator_user, monkeypatch):
    from app import agent_loop

    monkeypatch.setenv("ANTHROPIC_API_KEY", "mock-test-api-key")

    class MockAnthropicResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "stop_reason": "tool_use",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-123",
                        "name": "search_cases",
                        "input": {"query": "theft"},
                    }
                ],
            }

    # Mock requests.post to return tool_use endlessly
    monkeypatch.setattr("requests.post", lambda *args, **kwargs: MockAnthropicResponse())

    reply, action, steps = agent_loop.run_agent_loop(
        db=db_session,
        current_user=investigator_user,
        question="Run long search chain",
        context_blocks=["Sample case context"],
        session_id="test-session",
    )

    assert action is None
    assert "maximum agent reasoning depth (6 steps)" in steps[-1]
    assert "too complex" in reply.lower()



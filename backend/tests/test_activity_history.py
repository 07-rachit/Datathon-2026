"""
Test Suite for Persistent Activity History System.

Tests cover:
- Automatic activity recording via HTTP interceptor middleware
- Manual record_activity function with structured JSON metadata
- Search, Multi-field Filtering, Pagination, and Sorting
- Detailed Activity Record Inspection & Summary Statistics
- Immutability & Admin-Only Deletion Enforcement (RBAC)
- Sensitive Information Scrubbing in Activity Metadata
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.activity_logger import record_activity

client = TestClient(app)


def test_automatic_activity_recording(client, investigator_headers):
    """Verify HTTP requests automatically record an entry into persistent activity history."""
    case_payload = {
        "case_id": f"CASE-ACT-{datetime.utcnow().timestamp()}",
        "title": "Automated Activity Logging Case",
        "crime_type": "Theft",
        "district": "Patna",
        "station_name": "Kotwali PS",
        "incident_date": datetime.utcnow().isoformat(),
    }
    c_res = client.post("/api/cases", json=case_payload, headers=investigator_headers)
    assert c_res.status_code == 200

    # Fetch activity history
    h_res = client.get("/api/activity-history", headers=investigator_headers)
    assert h_res.status_code == 200
    data = h_res.json()
    assert data["total"] > 0
    assert len(data["results"]) > 0

    # Verify recorded fields
    first = data["results"][0]
    assert "activity_type" in first
    assert "module" in first
    assert first["status"] == "success"


def test_manual_activity_recording(db_session):
    """Verify record_activity helper persists records with sanitized metadata."""
    act = record_activity(
        db=db_session,
        activity_type="ai_generation",
        module="ai_assistant",
        title="AI Case Synthesis",
        description="Generated automated case summary report",
        user_id="test-user-id",
        user_name="Inspector Sharma",
        user_role="investigator",
        entity_type="case",
        entity_id="case-123",
        metadata={"prompt": "Summarize storyline A", "password": "super-secret-password-123"},
        status="success",
        execution_duration_ms=145.2,
    )

    assert act.id is not None
    assert act.module == "ai_assistant"
    assert act.execution_duration_ms == 145.2

    # Verify sensitive data was scrubbed
    assert "super-secret-password-123" not in act.metadata_json
    assert "***REDACTED***" in act.metadata_json


def test_activity_history_list_pagination_and_search(client, investigator_headers, db_session):
    """Verify searching, filtering, and pagination on activity history."""
    # Seed explicit test activity records
    rec1 = record_activity(
        db=db_session,
        activity_type="custom_search_type_alpha",
        module="analytics",
        title="District Crime Delta Calculation",
        description="Analyzed 30-day delta trends for Gaya district",
        status="success",
    )
    rec2 = record_activity(
        db=db_session,
        activity_type="custom_search_type_beta",
        module="finance",
        title="Money Laundering Wire Search",
        description="Scanned bank transfers above 5 Lakhs",
        status="failed",
    )

    # Free text search for "Gaya"
    search_res = client.get("/api/activity-history?q=Gaya", headers=investigator_headers)
    assert search_res.status_code == 200
    s_data = search_res.json()
    assert any("Gaya" in item["description"] for item in s_data["results"])

    # Filter by module=finance
    mod_res = client.get("/api/activity-history?module=finance", headers=investigator_headers)
    assert mod_res.status_code == 200
    m_data = mod_res.json()
    assert all(item["module"] == "finance" for item in m_data["results"])

    # Pagination test
    page_res = client.get("/api/activity-history?page=1&page_size=2", headers=investigator_headers)
    assert page_res.status_code == 200
    p_data = page_res.json()
    assert len(p_data["results"]) <= 2
    assert p_data["page"] == 1


def test_activity_detail_retrieval(client, investigator_headers, db_session):
    """Verify inspecting full details of an activity record."""
    act = record_activity(
        db=db_session,
        activity_type="detail_test",
        module="cases",
        title="Inspect Case Detail Event",
        description="Opened case CR-1002 for editing",
        status="success",
        metadata={"case_code": "CR-1002", "officer": "Inspector K. Sharma"},
    )

    det_res = client.get(f"/api/activity-history/{act.id}", headers=investigator_headers)
    assert det_res.status_code == 200
    detail = det_res.json()
    assert detail["id"] == act.id
    assert detail["title"] == "Inspect Case Detail Event"
    assert detail["metadata_json"]["case_code"] == "CR-1002"


def test_activity_history_rbac_and_immutability(client, investigator_headers, admin_headers, db_session):
    """Verify non-admin users cannot delete activity logs, enforcing immutability."""
    act = record_activity(
        db=db_session,
        activity_type="immutable_event",
        module="admin",
        title="Protected System Action",
        status="success",
    )

    # 1. Investigator attempt to delete fails with 403 AuthorizationError
    inv_del = client.delete(f"/api/activity-history/{act.id}", headers=investigator_headers)
    assert inv_del.status_code == 403
    assert inv_del.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    # 2. Admin attempt to delete succeeds with 204 No Content
    adm_del = client.delete(f"/api/activity-history/{act.id}", headers=admin_headers)
    assert adm_del.status_code == 204

    # 3. Verify deleted
    get_res = client.get(f"/api/activity-history/{act.id}", headers=admin_headers)
    assert get_res.status_code == 404


def test_activity_stats_summary(client, investigator_headers, db_session):
    """Verify summary metrics endpoint returns aggregate totals by module and status."""
    record_activity(db=db_session, activity_type="test_stats_1", module="cases", title="Stat Event 1", status="success")
    record_activity(db=db_session, activity_type="test_stats_2", module="ai_assistant", title="Stat Event 2", status="failed")

    res = client.get("/api/activity-history/stats/summary", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_activities" in data
    assert data["total_activities"] > 0
    assert "by_module" in data
    assert "by_status" in data

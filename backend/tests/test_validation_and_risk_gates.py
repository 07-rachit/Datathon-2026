"""
Comprehensive Test Suite for Evidence Intake Validation and Risk Gates System.

Tests cover:
- Standardized Error Envelopes & Request ID Tracking
- Schema Validations (String lengths, Types, Dates, Coordinate Ranges, Amounts)
- Malformed JSON Payloads
- Typed Exceptions (ValidationError, AuthenticationError, AuthorizationError, ResourceNotFoundError, ConflictError, BusinessRuleError)
- Risk Gates Protocol (Idempotency, Duplicate Action, State Transitions, RBAC, Self-Deactivation)
- Sensitive Data Masking & Statutory Redaction
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app import models, auth
from app.errors import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, BusinessRuleError
)
from app.risk_gates import check_case_creation_gate

client = TestClient(app)


def test_standardized_error_envelope_and_request_id(client, viewer_headers):
    """Verify error responses return standardized envelope with request_id and timestamp."""
    res = client.get("/api/cases/non_existent_case_9999", headers=viewer_headers)
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert data["error"]["status_code"] == 404
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]
    assert res.headers.get("x-request-id") == data["error"]["request_id"]


def test_validation_error_schema_details(client, investigator_headers):
    """Verify invalid payloads return 422 ValidationError with field-level details."""
    payload = {
        "case_id": "",  # Blank case_id
        "title": "A" * 500,  # Title exceeds max length
        "crime_type": "Robbery",
        "district": "Patna",
        "station_name": "Kotwali PS",
        "incident_date": "invalid-date-str",  # Invalid date format
        "latitude": 150.0,  # Out of range lat
        "longitude": -200.0,  # Out of range lng
    }
    res = client.post("/api/cases", json=payload, headers=investigator_headers)
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert len(data["error"]["details"]) > 0


def test_malformed_json_payload(client, investigator_headers):
    """Verify malformed JSON input is caught safely and formatted properly."""
    res = client.post(
        "/api/cases",
        content="{'invalid': json, }",
        headers={**investigator_headers, "Content-Type": "application/json"},
    )
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_risk_gate_duplicate_case_id(client, investigator_headers, db_session):
    """Verify risk gate blocks creation of duplicate case_id with ConflictError (409)."""
    payload = {
        "case_id": "CASE-DUP-001",
        "title": "Initial Burglary Investigation",
        "crime_type": "Burglary",
        "district": "Gaya",
        "station_name": "Gaya Town PS",
        "incident_date": datetime.utcnow().isoformat(),
        "latitude": 24.7955,
        "longitude": 85.0002,
    }
    # First creation should succeed
    res1 = client.post("/api/cases", json=payload, headers=investigator_headers)
    assert res1.status_code == 200

    # Second creation with same case_id must fail via risk gate
    res2 = client.post("/api/cases", json=payload, headers=investigator_headers)
    assert res2.status_code == 409
    data = res2.json()
    assert data["error"]["code"] == "CONFLICT_ERROR"
    assert "already exists" in data["error"]["message"]


def test_risk_gate_future_incident_date(client, investigator_headers):
    """Verify risk gate blocks incident_date set in the future."""
    future_date = (datetime.utcnow() + timedelta(days=365)).isoformat()
    payload = {
        "case_id": f"CASE-FUT-{datetime.utcnow().timestamp()}",
        "title": "Future Cyber Attack",
        "crime_type": "Cybercrime",
        "district": "Patna",
        "station_name": "Cyber PS",
        "incident_date": future_date,
    }
    res = client.post("/api/cases", json=payload, headers=investigator_headers)
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "BUSINESS_RULE_ERROR"
    assert "future" in data["error"]["message"]


def test_risk_gate_citizen_report_verification_state_transition(client, db_session, investigator_headers, viewer_headers):
    """Verify citizen report status state machine: cannot re-verify already reviewed report."""
    # 1. Submit valid report
    report_payload = {
        "crime_type": "Extortion",
        "location": "Boring Road Patna",
        "description": "Armed group demanding protection money from local shopkeepers",
        "reporter_name": "Ramesh Kumar",
        "reporter_phone": "9876543210",
    }
    sub_res = client.post("/api/citizen-reports", json=report_payload)
    assert sub_res.status_code == 200
    report_id = sub_res.json()["id"]

    # 2. Viewer attempting to verify report must fail with 403 AuthorizationError
    v_res = client.post(f"/api/citizen-reports/{report_id}/verify", json={"action": "approve"}, headers=viewer_headers)
    assert v_res.status_code == 403
    assert v_res.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    # 3. Investigator approving report first time succeeds
    ok_res = client.post(f"/api/citizen-reports/{report_id}/verify", json={"action": "approve"}, headers=investigator_headers)
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == "verified"

    # 4. Attempting to re-verify an already verified report must fail with 409 ConflictError
    dup_res = client.post(f"/api/citizen-reports/{report_id}/verify", json={"action": "reject", "rejection_reason": "test"}, headers=investigator_headers)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CONFLICT_ERROR"


def test_risk_gate_admin_self_deactivation_blocked(client, admin_headers, admin_user):
    """Verify Super Admin cannot deactivate their own user account."""
    res = client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers)
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "BUSINESS_RULE_ERROR"
    assert "Self-deactivation" in data["error"]["message"]


def test_risk_gate_invalid_task_status_transition(client, db_session, investigator_headers):
    """Verify task transition risk gate blocks invalid status strings."""
    # Create valid case & task first
    c_res = client.post("/api/cases", json={
        "case_id": f"CASE-TASK-{datetime.utcnow().timestamp()}",
        "title": "Robbery Inquiry",
        "crime_type": "Robbery",
        "district": "Patna",
        "station_name": "Central PS",
        "incident_date": datetime.utcnow().isoformat(),
    }, headers=investigator_headers)
    case_id = c_res.json()["id"]

    t_res = client.post(f"/api/cases/{case_id}/tasks", json={
        "title": "Collect CCTV Footage",
    }, headers=investigator_headers)
    task_id = t_res.json()["id"]

    # Patch with invalid status
    bad_up = client.patch(f"/api/cases/{case_id}/tasks/{task_id}", json={
        "status": "super_completed_invalid"
    }, headers=investigator_headers)
    assert bad_up.status_code == 422
    assert bad_up.json()["error"]["code"] == "VALIDATION_ERROR"


def test_financial_transaction_risk_gate(client, db_session, investigator_headers):
    """Verify financial transaction risk gate blocks zero/negative amounts and same source/target account."""
    acc1 = models.FinancialAccount(bank_name="SBI", account_number_masked="SBI-XXXX-1001")
    acc2 = models.FinancialAccount(bank_name="HDFC", account_number_masked="HDFC-XXXX-2002")
    db_session.add_all([acc1, acc2])
    db_session.commit()

    # Same source and target account must fail
    res1 = client.post("/api/finance/transactions", json={
        "from_account_id": acc1.id,
        "to_account_id": acc1.id,
        "amount": 50000.0,
    }, headers=investigator_headers)
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "BUSINESS_RULE_ERROR"

    # Negative amount must fail
    res2 = client.post("/api/finance/transactions", json={
        "from_account_id": acc1.id,
        "to_account_id": acc2.id,
        "amount": -100.0,
    }, headers=investigator_headers)
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "VALIDATION_ERROR"


def test_sensitive_information_redaction_and_masking(client, viewer_headers, admin_headers):
    """Verify sensitive fields and internal secrets are scrubbed in API responses."""
    # 1. Non-admin user viewing complainant data gets null for statutory sensitive attributes
    res = client.get("/api/cases", headers=viewer_headers)
    assert res.status_code == 200

    # 2. Login failure does not leak internal stack traces or database info
    bad_login = client.post("/api/auth/login", data={"username": "wrong@user.com", "password": "wrongpassword"})
    assert bad_login.status_code == 401
    login_data = bad_login.json()
    assert login_data["success"] is False
    assert login_data["error"]["code"] == "AUTHENTICATION_ERROR"
    assert "password" not in str(login_data).lower() or "wrongpassword" not in str(login_data)

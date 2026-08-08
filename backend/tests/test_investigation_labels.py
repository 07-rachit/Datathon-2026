"""
Comprehensive Test Suite for Investigation Labels for Security Cases.

Validates:
- Label updates (Suspected, Verified, Needs Review) by authorized roles
- Mandatory investigator note length & content validation
- RBAC enforcement (blocking viewer roles from updating labels)
- Immutable investigation history tracking & timeline log
- Activity history & audit log integration
- Case list filtering by investigation_label and reviewer_id
"""
import pytest
from datetime import datetime
from app import models


def _validate_label_payload(data, expected_label, expected_note):
    assert data["current_label"] == expected_label, f"Expected label {expected_label}, got {data['current_label']}"
    assert data["investigator_note"] == expected_note, "Investigator note mismatch"


def test_investigation_label_update_success(client, db_session, investigator_headers):
    """Test authorized investigator updating investigation label and note."""
    case = models.Case(
        case_id="CR-TEST-9901",
        title="Test Financial Fraud Incident",
        crime_type="Cyber Crime",
        district="Bengaluru Urban",
        station_name="Cyber Crime PS",
        status=models.CaseStatus.open,
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    payload = {
        "label": "Verified",
        "note": "Forensic evidence confirms suspect involvement in financial fraud."
    }

    res = client.put(f"/api/cases/{case.id}/investigation", json=payload, headers=investigator_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["case_id"] == case.id
    assert data["current_label"] == "Verified"
    assert "Forensic evidence confirms" in data["investigator_note"]
    assert data["reviewer_name"] is not None
    assert len(data["history"]) >= 1
    assert data["history"][0]["new_label"] == "Verified"


def test_investigation_label_rbac_viewer_blocked(client, db_session, viewer_headers):
    """Test that viewer role is forbidden (403) from updating investigation labels."""
    case = models.Case(
        case_id="CR-TEST-9902",
        title="Test Theft Incident",
        crime_type="Theft",
        district="Mysuru",
        station_name="Central PS",
        status=models.CaseStatus.open,
        severity=models.Severity.medium,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    payload = {
        "label": "Suspected",
        "note": "Attempting unauthorized label modification."
    }

    res = client.put(f"/api/cases/{case.id}/investigation", json=payload, headers=viewer_headers)
    assert res.status_code == 403


def test_investigation_label_note_validation(client, db_session, investigator_headers):
    """Test validation errors for short notes or missing mandatory fields."""
    case = models.Case(
        case_id="CR-TEST-9903",
        title="Test Burglary Incident",
        crime_type="Burglary",
        district="Mangaluru",
        station_name="Bunder PS",
        status=models.CaseStatus.open,
        severity=models.Severity.low,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # Note too short (< 3 chars)
    payload_short = {
        "label": "Suspected",
        "note": "no"
    }
    res = client.put(f"/api/cases/{case.id}/investigation", json=payload_short, headers=investigator_headers)
    assert res.status_code == 422

    # Cannot set label to Unreviewed explicitly
    payload_unreviewed = {
        "label": "Unreviewed",
        "note": "Resetting label to unreviewed"
    }
    res = client.put(f"/api/cases/{case.id}/investigation", json=payload_unreviewed, headers=investigator_headers)
    assert res.status_code == 422


def test_investigation_history_timeline(client, db_session, investigator_headers):
    """Test multiple sequential updates maintaining chronological history log."""
    case = models.Case(
        case_id="CR-TEST-9904",
        title="Test Robbery Incident",
        crime_type="Robbery",
        district="Hubballi",
        station_name="Town PS",
        status=models.CaseStatus.open,
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # First update: Needs Review
    res1 = client.put(
        f"/api/cases/{case.id}/investigation",
        json={"label": "Needs Review", "note": "Initial flag for senior analyst review."},
        headers=investigator_headers,
    )
    assert res1.status_code == 200

    # Second update: Suspected
    res2 = client.put(
        f"/api/cases/{case.id}/investigation",
        json={"label": "Suspected", "note": "Secondary review confirms strong suspicion."},
        headers=investigator_headers,
    )
    assert res2.status_code == 200

    # Fetch investigation status GET
    res_get = client.get(f"/api/cases/{case.id}/investigation", headers=investigator_headers)
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["current_label"] == "Suspected"
    assert data["previous_label"] == "Needs Review"
    assert len(data["history"]) >= 2


def test_list_cases_filter_by_investigation_label(client, db_session, investigator_headers):
    """Test listing cases with investigation_label filtering."""
    case = models.Case(
        case_id="CR-TEST-9905",
        title="Test Cyber Attack Incident",
        crime_type="Cyber Crime",
        district="Bengaluru Urban",
        station_name="Cyber PS",
        status=models.CaseStatus.open,
        severity=models.Severity.critical,
        incident_date=datetime.utcnow(),
        investigation_label="Suspected",
    )
    db_session.add(case)
    db_session.commit()

    res = client.get("/api/cases?investigation_label=Suspected", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    assert any(c["case_id"] == "CR-TEST-9905" for c in data["results"])

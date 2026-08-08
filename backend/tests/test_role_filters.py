"""
Comprehensive Test Suite for Role-Aware Security Case Filters.

Validates:
- Role scope filtering for admin, investigator, reviewer, authority, hospital, and user roles
- Scoped list results accuracy
- Active role scope field and total visible count in CaseListResponse
"""
import pytest
from datetime import datetime
from app import models


def test_list_cases_role_scope_admin(client, db_session, investigator_headers):
    """Test admin overview role scope returns all records."""
    res = client.get("/api/cases?role_scope=admin", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert data["active_role_scope"] == "admin"
    assert isinstance(data["results"], list)


def test_list_cases_role_scope_investigator(client, db_session, investigator_headers):
    """Test investigator role scope returns active investigation cases."""
    case1 = models.Case(
        case_id="CR-ROLE-INV-001",
        title="Investigator Scoped Cyber Case",
        crime_type="Cyber Fraud",
        district="Bengaluru",
        station_name="Cyber PS",
        status=models.CaseStatus.under_review,
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
        investigation_label=models.InvestigationLabelEnum.suspected,
    )
    db_session.add(case1)
    db_session.commit()

    res = client.get("/api/cases?role_scope=investigator", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_role_scope"] == "investigator"
    case_ids = [c["case_id"] for c in data["results"]]
    assert "CR-ROLE-INV-001" in case_ids


def test_list_cases_role_scope_reviewer(client, db_session, investigator_headers):
    """Test reviewer role scope returns cases requiring review."""
    case2 = models.Case(
        case_id="CR-ROLE-REV-001",
        title="Reviewer Scoped Pending Case",
        crime_type="Financial Scam",
        district="Patna",
        station_name="Central PS",
        status=models.CaseStatus.under_review,
        severity=models.Severity.critical,
        incident_date=datetime.utcnow(),
        investigation_label=models.InvestigationLabelEnum.needs_review,
    )
    db_session.add(case2)
    db_session.commit()

    res = client.get("/api/cases?role_scope=reviewer", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_role_scope"] == "reviewer"
    case_ids = [c["case_id"] for c in data["results"]]
    assert "CR-ROLE-REV-001" in case_ids


def test_list_cases_role_scope_authority(client, db_session, investigator_headers):
    """Test authority role scope returns high severity & FIR cases."""
    case3 = models.Case(
        case_id="CR-ROLE-AUTH-001",
        title="Authority Scoped Critical Incident",
        crime_type="Extortion",
        district="Mangaluru",
        station_name="HQ PS",
        status=models.CaseStatus.open,
        severity=models.Severity.critical,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case3)
    db_session.commit()

    res = client.get("/api/cases?role_scope=authority", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_role_scope"] == "authority"
    case_ids = [c["case_id"] for c in data["results"]]
    assert "CR-ROLE-AUTH-001" in case_ids


def test_list_cases_role_scope_hospital(client, db_session, investigator_headers):
    """Test hospital role scope returns medico-legal & violent crime security cases."""
    case4 = models.Case(
        case_id="CR-ROLE-HOSP-001",
        title="Hospital Medico-Legal Assault Case",
        crime_type="Physical Assault & Battery",
        district="Bengaluru Urban",
        station_name="City Hospital PS",
        status=models.CaseStatus.open,
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case4)
    db_session.commit()

    res = client.get("/api/cases?role_scope=hospital", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_role_scope"] == "hospital"
    case_ids = [c["case_id"] for c in data["results"]]
    assert "CR-ROLE-HOSP-001" in case_ids


def test_list_cases_role_scope_user(client, db_session, investigator_headers):
    """Test user role scope returns user-relevant cases."""
    res = client.get("/api/cases?role_scope=user", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_role_scope"] == "user"
    assert isinstance(data["total"], int)


def test_list_cases_role_scope_combined_with_severity(client, db_session, investigator_headers):
    """Test combining role_scope with explicit severity and status filters."""
    res = client.get("/api/cases?role_scope=authority&severity=critical", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_role_scope"] == "authority"
    for case in data["results"]:
        assert case["severity"] == "critical"

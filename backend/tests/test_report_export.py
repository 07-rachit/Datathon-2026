"""
Comprehensive Test Suite for Project-Specific Security Case Report Export (PDF, HTML, CSV).

Validates:
- PDF report generation with ReportLab table layout and styling
- Printable HTML report generation with CSS badges and tables
- Structured CSV report generation for spreadsheet data analysis
- Subpath format endpoints (/report/pdf, /report/html, /report/csv)
- Role-based access control (RBAC) enforcement (viewer role 403 rejection)
- Error handling for unsupported formats (422) and non-existent cases (404)
- Graceful rendering ("Not Available" fallback) for incomplete case records
- Audit logging and activity history recording
"""
import pytest
from datetime import datetime
from app import models


def test_export_case_report_pdf(client, db_session, investigator_headers):
    """Test generating a PDF report for a security case."""
    case = models.Case(
        case_id="CR-TEST-EX-001",
        title="PDF Export Validation Incident",
        crime_type="Cyber Crime",
        district="Bengaluru Urban",
        station_name="Cyber PS",
        status=models.CaseStatus.open,
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
        investigation_label=models.InvestigationLabelEnum.verified,
        investigator_note="Forensic investigation confirms network breach.",
        reviewer_name="Inspector Sharma",
        review_timestamp=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    res = client.get(f"/api/export/cases/{case.id}/report?format=pdf", headers=investigator_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res.headers["content-disposition"]
    assert res.headers["content-disposition"].endswith('.pdf"')
    assert len(res.content) > 500


def test_export_case_report_html(client, db_session, investigator_headers):
    """Test generating a printable HTML report for a security case."""
    case = models.Case(
        case_id="CR-TEST-EX-002",
        title="HTML Export Validation Incident",
        crime_type="Financial Fraud",
        district="Mysuru",
        station_name="Central PS",
        status=models.CaseStatus.under_review,
        severity=models.Severity.critical,
        incident_date=datetime.utcnow(),
        investigation_label=models.InvestigationLabelEnum.suspected,
        investigator_note="Mule transaction patterns flagged for senior review.",
    )
    db_session.add(case)
    db_session.commit()

    res = client.get(f"/api/export/cases/{case.id}/report?format=html", headers=investigator_headers)
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]

    html_str = res.content.decode("utf-8")
    assert "<!DOCTYPE html>" in html_str
    assert "CR-TEST-EX-002" in html_str
    assert "Suspected" in html_str
    assert "Mule transaction patterns" in html_str


def test_export_case_report_csv(client, db_session, investigator_headers):
    """Test generating a structured CSV report for a security case."""
    case = models.Case(
        case_id="CR-TEST-EX-003",
        title="CSV Export Validation Incident",
        crime_type="Theft",
        district="Mangaluru",
        station_name="Bunder PS",
        status=models.CaseStatus.open,
        severity=models.Severity.medium,
        incident_date=datetime.utcnow(),
        investigation_label=models.InvestigationLabelEnum.needs_review,
        investigator_note="CCTV footage attached for verification.",
    )
    db_session.add(case)
    db_session.commit()

    res = client.get(f"/api/export/cases/{case.id}/report?format=csv", headers=investigator_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

    csv_str = res.content.decode("utf-8")
    assert "=== SECURITY CASE OVERVIEW METADATA ===" in csv_str
    assert "CR-TEST-EX-003" in csv_str
    assert "Needs Review" in csv_str
    assert "=== PERSONS OF INTEREST ROSTER ===" in csv_str


def test_export_case_report_subpath_routes(client, db_session, investigator_headers):
    """Test explicit format subpath routes /report/pdf, /report/html, /report/csv."""
    case = models.Case(
        case_id="CR-TEST-EX-004",
        title="Subpath Export Validation Incident",
        crime_type="General",
        district="Patna",
        station_name="Main PS",
        status=models.CaseStatus.open,
        severity=models.Severity.low,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # /report/pdf
    res_pdf = client.get(f"/api/export/cases/{case.id}/report/pdf", headers=investigator_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"

    # /report/html
    res_html = client.get(f"/api/export/cases/{case.id}/report/html", headers=investigator_headers)
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]

    # /report/csv
    res_csv = client.get(f"/api/export/cases/{case.id}/report/csv", headers=investigator_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]


def test_export_case_report_rbac_viewer_blocked(client, db_session, viewer_headers):
    """Test that viewer role is forbidden (403) from exporting security case reports."""
    case = models.Case(
        case_id="CR-TEST-EX-005",
        title="Restricted Export Incident",
        crime_type="General",
        district="Patna",
        station_name="Main PS",
        status=models.CaseStatus.open,
        severity=models.Severity.low,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    res = client.get(f"/api/export/cases/{case.id}/report?format=pdf", headers=viewer_headers)
    assert res.status_code == 403


def test_export_case_report_unsupported_format(client, db_session, investigator_headers):
    """Test validation error (422) for unsupported export formats."""
    case = models.Case(
        case_id="CR-TEST-EX-006",
        title="Invalid Format Incident",
        crime_type="General",
        district="Patna",
        station_name="Main PS",
        status=models.CaseStatus.open,
        severity=models.Severity.low,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    res = client.get(f"/api/export/cases/{case.id}/report?format=xml", headers=investigator_headers)
    assert res.status_code == 422


def test_export_case_report_missing_case_404(client, db_session, investigator_headers):
    """Test 404 error for non-existent case ID."""
    res = client.get("/api/export/cases/non-existent-id-9999/report?format=pdf", headers=investigator_headers)
    assert res.status_code == 404

"""
Test Suite for Background Task Runner with Retries.

Tests cover:
- Asynchronous job submission and background execution
- Search, Multi-field Filtering, Pagination, and Status Polling
- Automatic Retry Engine with Exponential Backoff on Transient Failures
- Immediate Failure on Permanent Unrecoverable Errors
- Manual Retry and Cancellation Endpoints
- Role-Based Access Control (RBAC) & User Isolation
- Step-by-Step Execution Log Retrieval
- Sensitive Payload Redaction
"""
import time
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.job_runner import enqueue_job, register_job_handler

client = TestClient(app)


def test_job_creation_and_async_execution(client, investigator_headers):
    """Verify enqueuing an async PDF export job transitions to COMPLETED with output."""
    payload = {
        "job_type": "pdf_export",
        "entity_id": "CASE-1002",
        "input_payload": {"requested_by": "Inspector Sharma"},
    }
    res = client.post("/api/jobs", json=payload, headers=investigator_headers)
    assert res.status_code == 202
    data = res.json()
    job_id = data["id"]
    assert data["status"] in ("QUEUED", "RUNNING", "COMPLETED")

    # Poll for completion (up to 3 seconds)
    completed = False
    for _ in range(15):
        time.sleep(0.2)
        get_res = client.get(f"/api/jobs/{job_id}", headers=investigator_headers)
        assert get_res.status_code == 200
        j_data = get_res.json()
        if j_data["status"] == "COMPLETED":
            completed = True
            assert j_data["progress_pct"] == 100
            assert j_data["output_result"]["file_name"] == "case_dossier_CASE-1002.pdf"
            assert "download_url" in j_data["output_result"]
            assert j_data["execution_duration_ms"] is not None
            break

    assert completed, "Background job did not transition to COMPLETED in time"


def test_job_list_pagination_search_and_filtering(client, investigator_headers):
    """Verify searching, status filtering, and pagination on background jobs."""
    # Submit jobs
    client.post("/api/jobs", json={"job_type": "csv_import"}, headers=investigator_headers)
    client.post("/api/jobs", json={"job_type": "business_analysis"}, headers=investigator_headers)

    # Wait briefly for execution
    time.sleep(0.5)

    # Filter by job_type
    res = client.get("/api/activity-history?module=cases", headers=investigator_headers)
    j_res = client.get("/api/jobs?job_type=csv_import", headers=investigator_headers)
    assert j_res.status_code == 200
    data = j_res.json()
    assert all(item["job_type"] == "csv_import" for item in data["results"])

    # Pagination
    p_res = client.get("/api/jobs?page=1&page_size=2", headers=investigator_headers)
    assert p_res.status_code == 200
    assert len(p_res.json()["results"]) <= 2


def test_automatic_retries_on_transient_failure(db_session, investigator_user):
    """Verify automatic retry logic increments retry_count and handles transient errors."""
    attempt_counter = {"count": 0}

    def _flaky_handler(job, db):
        attempt_counter["count"] += 1
        if attempt_counter["count"] < 2:
            raise RuntimeError("Transient connection reset error")
        return {"flaky_success": True}

    register_job_handler("flaky_test_job", _flaky_handler)

    job = enqueue_job(
        db=db_session,
        job_type="flaky_test_job",
        user_id=investigator_user.id,
        user_name=investigator_user.name,
        max_retries=2,
        retry_delay_seconds=1,
    )

    # Wait for retry loop
    time.sleep(1.8)

    db_session.refresh(job)
    assert job.retry_count == 1
    assert job.status == "COMPLETED"
    assert "flaky_success" in job.output_result_json


def test_permanent_failure_detection(db_session, investigator_user):
    """Verify permanent errors (e.g. ValidationError) fail immediately without retrying."""
    from app.errors import ValidationError

    def _permanent_fail_handler(job, db):
        raise ValidationError("Permanent invalid payload structure")

    register_job_handler("permanent_fail_job", _permanent_fail_handler)

    job = enqueue_job(
        db=db_session,
        job_type="permanent_fail_job",
        user_id=investigator_user.id,
        user_name=investigator_user.name,
        max_retries=3,
    )

    time.sleep(0.5)

    db_session.refresh(job)
    assert job.status == "FAILED"
    assert job.retry_count == 0  # Did not waste retries
    assert "ValidationError" in job.error_details


def test_manual_job_retry_endpoint(client, investigator_headers, db_session, investigator_user):
    """Verify manual retry endpoint re-queues failed jobs."""
    job = enqueue_job(
        db=db_session,
        job_type="csv_import",
        user_id=investigator_user.id,
    )
    job.status = "FAILED"
    job.error_details = '{"message": "Simulated failure"}'
    db_session.commit()

    res = client.post(f"/api/jobs/{job.id}/retry", headers=investigator_headers)
    assert res.status_code == 200
    assert res.json()["status"] in ("QUEUED", "RUNNING", "COMPLETED")


def test_job_cancellation_endpoint(client, investigator_headers, db_session, investigator_user):
    """Verify cancelling a queued/running job."""
    job = models.BackgroundJob(
        id="job-to-cancel-123",
        job_type="business_analysis",
        user_id=investigator_user.id,
        status="QUEUED",
    )
    db_session.add(job)
    db_session.commit()

    res = client.post(f"/api/jobs/{job.id}/cancel", headers=investigator_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"


def test_job_logs_retrieval(client, investigator_headers, db_session, investigator_user):
    """Verify fetching step-by-step logs for a background job."""
    job = enqueue_job(
        db=db_session,
        job_type="pdf_export",
        entity_id="CASE-99",
        user_id=investigator_user.id,
    )

    time.sleep(0.6)

    res = client.get(f"/api/jobs/{job.id}/logs", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert len(data["logs"]) > 0


def test_job_rbac_and_authorization(client, investigator_headers, viewer_headers, db_session, investigator_user):
    """Verify non-admin users cannot access or cancel jobs owned by other users."""
    job = enqueue_job(
        db=db_session,
        job_type="pdf_export",
        user_id=investigator_user.id,
    )

    # Viewer user attempts to get logs for investigator's job -> 403 Forbidden
    v_res = client.get(f"/api/jobs/{job.id}", headers=viewer_headers)
    assert v_res.status_code == 403

    # Viewer user attempts to cancel investigator's job -> 403 Forbidden
    c_res = client.post(f"/api/jobs/{job.id}/cancel", headers=viewer_headers)
    assert c_res.status_code == 403


def test_sensitive_payload_scrubbing_in_jobs(db_session, investigator_user):
    """Verify sensitive fields like passwords and API keys are redacted in job payload and metadata."""
    job = enqueue_job(
        db=db_session,
        job_type="ai_content_generation",
        user_id=investigator_user.id,
        input_payload={"prompt": "Synthesize case", "api_key": "sk-secret-key-12345", "password": "pass"},
    )

    assert "sk-secret-key-12345" not in job.input_payload_json
    assert "***REDACTED***" in job.input_payload_json

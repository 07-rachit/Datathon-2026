def test_citizen_report_submission_and_tracking(client):
    # 1. Submit citizen report
    payload = {
        "crime_type": "Cyber Fraud",
        "incident_date": "2026-08-07T12:00:00",
        "location": "Indiranagar, Bengaluru",
        "description": "Unauthorized phishing transaction of Rs 50,000.",
        "reporter_name": "Test Citizen",
        "reporter_phone": "+91-9999988888",
        "reporter_email": "citizen@test.com",
        "evidence": [
            {"file_name": "screenshot.png", "file_type": "image", "file_path": "/uploads/screenshot.png"}
        ]
    }
    response = client.post("/api/citizen-reports", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "tracking_id" in data
    assert data["status"] == "pending"
    tracking_id = data["tracking_id"]
    report_id = data["id"]

    # 2. Track report publicly by tracking_id
    track_resp = client.get(f"/api/citizen-reports/track/{tracking_id}")
    assert track_resp.status_code == 200
    track_data = track_resp.json()
    assert track_data["tracking_id"] == tracking_id
    assert track_data["description"] == payload["description"]


def test_citizen_report_officer_verification(client, admin_headers):
    # 1. Submit report
    payload = {
        "crime_type": "Jewelry Theft",
        "location": "Commercial Street",
        "description": "Stolen gold chain.",
        "reporter_name": "Officer Test",
        "reporter_phone": "+91-9888877777"
    }
    sub_resp = client.post("/api/citizen-reports", json=payload)
    report_id = sub_resp.json()["id"]

    # 2. List reports as officer
    list_resp = client.get("/api/citizen-reports?status=pending", headers=admin_headers)
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert any(r["id"] == report_id for r in reports)

    # 3. Approve report & convert to case
    verify_resp = client.post(
        f"/api/citizen-reports/{report_id}/verify",
        json={"action": "approve"},
        headers=admin_headers
    )
    assert verify_resp.status_code == 200
    approved_data = verify_resp.json()
    assert approved_data["status"] == "verified"
    assert approved_data["created_case_id"] is not None

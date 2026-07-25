from datetime import datetime
from app import models

def test_create_case_investigator(client, investigator_headers):
    payload = {
        "case_id": "CR-2026-TEST",
        "title": "Test Burglary",
        "crime_type": "Burglary",
        "district": "Ludhiana East",
        "station_name": "PS Division 1",
        "status": "open",
        "severity": "high",
        "incident_date": datetime.utcnow().isoformat(),
        "summary": "Sample summary for test case.",
    }
    response = client.post("/api/cases", json=payload, headers=investigator_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "CR-2026-TEST"


def test_create_case_forbidden_viewer(client, viewer_headers):
    payload = {
        "case_id": "CR-2026-FAIL",
        "title": "Unauthorized Case",
        "crime_type": "Theft",
        "district": "Ludhiana West",
        "station_name": "PS Division 3",
        "incident_date": datetime.utcnow().isoformat(),
    }
    response = client.post("/api/cases", json=payload, headers=viewer_headers)
    assert response.status_code == 403


def test_phone_number_masking_viewer(client, db_session, investigator_headers, viewer_headers):
    case = models.Case(
        case_id="CR-2026-MASK",
        title="Mask Test",
        crime_type="Fraud",
        district="Model Town",
        station_name="PS Model Town",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.flush()

    person = models.Person(
        case_id=case.id,
        name="Secret Suspect",
        role_in_case="suspect",
        phone_number="+91-9876543210",
    )
    db_session.add(person)
    db_session.commit()

    # Investigator gets full phone number
    inv_res = client.get(f"/api/cases/{case.id}", headers=investigator_headers)
    assert inv_res.status_code == 200
    assert inv_res.json()["persons"][0]["phone_number"] == "+91-9876543210"

    # Viewer gets masked phone number ending in ******
    view_res = client.get(f"/api/cases/{case.id}", headers=viewer_headers)
    assert view_res.status_code == 200
    assert view_res.json()["persons"][0]["phone_number"] == "+91-9876******"

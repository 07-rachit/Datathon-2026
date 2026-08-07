from datetime import datetime
from app import models

def test_export_case_pdf(client, db_session, investigator_headers):
    case = models.Case(
        case_id="CR-2026-PDF",
        title="PDF Export Test",
        crime_type="Theft",
        district="Civil Lines",
        station_name="PS Civil Lines",
        incident_date=datetime.utcnow(),
        summary="PDF summary test.",
    )
    db_session.add(case)
    db_session.commit()

    res = client.get(f"/api/export/cases/{case.id}/report", headers=investigator_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 100

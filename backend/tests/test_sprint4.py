from datetime import datetime
from app import models

def test_case_timeline_endpoint(client, db_session, investigator_headers):
    case = models.Case(
        case_id="CR-2026-TLTEST",
        title="Timeline Test Case",
        crime_type="Assault",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    res = client.get(f"/api/cases/{case.id}/timeline", headers=investigator_headers)
    assert res.status_code == 200
    timeline = res.json()
    assert len(timeline) >= 1
    assert timeline[0]["event_type"] == "incident_occurred"


def test_network_groups_endpoint(client, db_session, investigator_headers):
    res = client.get("/api/network/groups", headers=investigator_headers)
    assert res.status_code == 200
    groups = res.json()
    assert isinstance(groups, list)


def test_seasonal_trends_endpoint(client, investigator_headers):
    res = client.get("/api/analytics/seasonal-trends", headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert "monthly_trends" in data
    assert len(data["monthly_trends"]) == 12
    assert "weekday_trends" in data
    assert len(data["weekday_trends"]) == 7
    assert "high_context_events" in data

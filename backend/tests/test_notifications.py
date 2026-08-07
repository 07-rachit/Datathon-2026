from datetime import datetime
from app import models, auth


def test_high_severity_case_notification_and_rbac_scoping(
    client, db_session, investigator_user, investigator_headers, admin_user, admin_headers, viewer_user, viewer_headers
):
    # 1. Investigator creates a CRITICAL severity case
    payload = {
        "case_id": "CR-2026-NOTIF1",
        "title": "Armed Robbery at Jeweller Shop",
        "crime_type": "Robbery",
        "district": "Bengaluru City",
        "station_name": "PS Central",
        "severity": "critical",
        "incident_date": datetime.utcnow().isoformat(),
        "summary": "Suspects armed with knives looted cash counter.",
    }
    res = client.post("/api/cases", json=payload, headers=investigator_headers)
    assert res.status_code == 200

    # 2. Admin should receive a high_severity_case notification
    res_admin = client.get("/api/notifications", headers=admin_headers)
    assert res_admin.status_code == 200
    admin_notifs = res_admin.json()
    assert len(admin_notifs) >= 1
    assert any(n["type"] == "high_severity_case" and "CR-2026-NOTIF1" in n["title"] for n in admin_notifs)

    # 3. Viewer should NOT receive high_severity_case notification (viewer excluded)
    res_viewer = client.get("/api/notifications", headers=viewer_headers)
    assert res_viewer.status_code == 200
    viewer_notifs = res_viewer.json()
    assert not any(n["type"] == "high_severity_case" and "CR-2026-NOTIF1" in n["title"] for n in viewer_notifs)


def test_case_assignment_notification(
    client, db_session, admin_headers, investigator_user, investigator_headers
):
    # Create test case
    case = models.Case(
        case_id="CR-2026-NASSIGN",
        title="Warehouse Breakin",
        crime_type="Burglary",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # Admin assigns investigator as "Lead Investigator"
    res_assign = client.post(
        f"/api/cases/{case.id}/assignments",
        json={"assigned_to_user_id": investigator_user.id, "role_on_case": "Lead Investigator"},
        headers=admin_headers,
    )
    assert res_assign.status_code == 200

    # Check investigator notifications
    res_notif = client.get("/api/notifications", headers=investigator_headers)
    assert res_notif.status_code == 200
    notifs = res_notif.json()
    assert len(notifs) >= 1
    assert any(n["type"] == "case_assigned" and "CR-2026-NASSIGN" in n["title"] for n in notifs)


def test_task_assignment_notification(
    client, db_session, admin_headers, investigator_user, investigator_headers
):
    case = models.Case(
        case_id="CR-2026-NTASK",
        title="Cyber Phishing Case",
        crime_type="Fraud",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # Admin assigns task to investigator
    res_task = client.post(
        f"/api/cases/{case.id}/tasks",
        json={"title": "Analyze IP logs", "assigned_to_user_id": investigator_user.id},
        headers=admin_headers,
    )
    assert res_task.status_code == 200

    # Check investigator notifications
    res_notif = client.get("/api/notifications", headers=investigator_headers)
    assert res_notif.status_code == 200
    notifs = res_notif.json()
    assert len(notifs) >= 1
    assert any(n["type"] == "task_assigned" and "Analyze IP logs" in n["message"] for n in notifs)


def test_notification_rest_endpoints(
    client, db_session, investigator_user, investigator_headers
):
    # Seed sample notifications directly
    n1 = models.Notification(
        user_id=investigator_user.id,
        type="task_assigned",
        title="Task 1",
        message="Message 1",
        is_read=False,
    )
    n2 = models.Notification(
        user_id=investigator_user.id,
        type="case_assigned",
        title="Task 2",
        message="Message 2",
        is_read=False,
    )
    db_session.add_all([n1, n2])
    db_session.commit()

    # 1. Check unread count
    res_count = client.get("/api/notifications/unread-count", headers=investigator_headers)
    assert res_count.status_code == 200
    assert res_count.json()["unread_count"] >= 2

    # 2. Mark n1 as read
    res_read = client.patch(f"/api/notifications/{n1.id}/read", headers=investigator_headers)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # 3. Mark all read
    res_all = client.patch("/api/notifications/read-all", headers=investigator_headers)
    assert res_all.status_code == 200

    # Unread count should now be 0
    res_count_after = client.get("/api/notifications/unread-count", headers=investigator_headers)
    assert res_count_after.status_code == 200
    assert res_count_after.json()["unread_count"] == 0

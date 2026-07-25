from datetime import datetime
from app import models, auth


def test_comment_lifecycle_and_rbac(client, db_session, investigator_user, investigator_headers, viewer_headers):
    # Create test case
    case = models.Case(
        case_id="CR-2026-COMM",
        title="Comment Test Case",
        crime_type="Theft",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # 1. Investigator posts comment
    res = client.post(
        f"/api/cases/{case.id}/comments",
        json={"content": "Investigator initial observation"},
        headers=investigator_headers,
    )
    assert res.status_code == 200
    c_data = res.json()
    assert c_data["content"] == "Investigator initial observation"
    assert c_data["author_name"] == investigator_user.name
    comment_id = c_data["id"]

    # 2. List comments
    res_list = client.get(f"/api/cases/{case.id}/comments", headers=investigator_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 3. Viewer attempts to post comment -> 403
    res_viewer = client.post(
        f"/api/cases/{case.id}/comments",
        json={"content": "Viewer comment"},
        headers=viewer_headers,
    )
    assert res_viewer.status_code == 403

    # 4. Author deletes comment -> 200
    res_del = client.delete(f"/api/cases/{case.id}/comments/{comment_id}", headers=investigator_headers)
    assert res_del.status_code == 200


def test_assignment_rbac_enforcement(client, db_session, admin_user, admin_headers, investigator_user, investigator_headers, viewer_headers):
    # Create test case
    case = models.Case(
        case_id="CR-2026-ASSIGN",
        title="Assignment Test Case",
        crime_type="Robbery",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # 1. Admin assigns investigator to case -> 200
    res_admin = client.post(
        f"/api/cases/{case.id}/assignments",
        json={"assigned_to_user_id": investigator_user.id, "role_on_case": "Lead Investigator"},
        headers=admin_headers,
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["role_on_case"] == "Lead Investigator"

    # 2. Investigator attempts to assign another user (admin_user) -> 403 Forbidden
    res_inv_fail = client.post(
        f"/api/cases/{case.id}/assignments",
        json={"assigned_to_user_id": admin_user.id, "role_on_case": "Supporting Officer"},
        headers=investigator_headers,
    )
    assert res_inv_fail.status_code == 403
    assert "Investigators can only self-claim cases" in res_inv_fail.json()["detail"]

    # 3. Investigator self-claims case -> 200
    res_inv_self = client.post(
        f"/api/cases/{case.id}/assignments",
        json={"assigned_to_user_id": investigator_user.id, "role_on_case": "Supporting Officer"},
        headers=investigator_headers,
    )
    assert res_inv_self.status_code == 200

    # 4. Viewer attempts to assign -> 403
    res_viewer = client.post(
        f"/api/cases/{case.id}/assignments",
        json={"assigned_to_user_id": investigator_user.id, "role_on_case": "Supporting Officer"},
        headers=viewer_headers,
    )
    assert res_viewer.status_code == 403


def test_task_lifecycle_and_status_permissions(client, db_session, admin_user, admin_headers, investigator_user, investigator_headers, viewer_user):
    # Create analyst user
    analyst_user = models.User(
        name="Analyst Test",
        email="analyst@test.local",
        hashed_password=auth.hash_password("password123"),
        role=models.RoleEnum.analyst,
    )
    db_session.add(analyst_user)
    db_session.commit()

    case = models.Case(
        case_id="CR-2026-TASK",
        title="Task Test Case",
        crime_type="Fraud",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # 1. Admin creates task assigned to investigator_user
    res_create = client.post(
        f"/api/cases/{case.id}/tasks",
        json={
            "title": "Verify bank transfer receipt",
            "description": "Cross-check IMPS transaction ref number",
            "assigned_to_user_id": investigator_user.id,
        },
        headers=admin_headers,
    )
    assert res_create.status_code == 200
    task_data = res_create.json()
    assert task_data["status"] == "todo"
    task_id = task_data["id"]

    # 2. Investigator updates task status to "in_progress" -> 200
    res_update = client.patch(
        f"/api/cases/{case.id}/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=investigator_headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "in_progress"

    # 3. Investigator marks task "done" -> 200, completed_at set
    res_done = client.patch(
        f"/api/cases/{case.id}/tasks/{task_id}",
        json={"status": "done"},
        headers=investigator_headers,
    )
    assert res_done.status_code == 200
    assert res_done.json()["status"] == "done"
    assert res_done.json()["completed_at"] is not None


def test_my_work_endpoints(client, db_session, admin_user, admin_headers, investigator_user, investigator_headers):
    case = models.Case(
        case_id="CR-2026-WORK",
        title="My Work Test Case",
        crime_type="Burglary",
        district="Mysuru",
        station_name="PS Central",
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # Assign case to investigator
    client.post(
        f"/api/cases/{case.id}/assignments",
        json={"assigned_to_user_id": investigator_user.id, "role_on_case": "Lead Investigator"},
        headers=admin_headers,
    )

    # Create open task assigned to investigator
    client.post(
        f"/api/cases/{case.id}/tasks",
        json={
            "title": "Scan burglary footprints",
            "assigned_to_user_id": investigator_user.id,
        },
        headers=admin_headers,
    )

    # 1. GET /api/me/tasks
    res_tasks = client.get("/api/me/tasks", headers=investigator_headers)
    assert res_tasks.status_code == 200
    tasks = res_tasks.json()
    assert len(tasks) >= 1
    assert any(t["title"] == "Scan burglary footprints" for t in tasks)

    # 2. GET /api/me/assigned-cases
    res_cases = client.get("/api/me/assigned-cases", headers=investigator_headers)
    assert res_cases.status_code == 200
    cases = res_cases.json()
    assert len(cases) >= 1
    assert any(c["case_code"] == "CR-2026-WORK" for c in cases)

def test_admin_list_users(client, admin_headers, admin_user):
    response = client.get("/api/admin/users", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_admin_list_users_forbidden(client, investigator_headers):
    response = client.get("/api/admin/users", headers=investigator_headers)
    assert response.status_code == 403


def test_admin_create_user(client, admin_headers):
    payload = {
        "name": "New Analyst",
        "email": "analyst@test.com",
        "password": "password123",
        "role": "analyst",
    }
    response = client.post("/api/admin/users", json=payload, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["role"] == "analyst"


def test_admin_update_user_role(client, admin_headers, viewer_user):
    response = client.patch(
        f"/api/admin/users/{viewer_user.id}",
        json={"role": "investigator"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "investigator"


def test_admin_deactivate_self_blocked(client, admin_headers, admin_user):
    response = client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers)
    assert response.status_code == 400

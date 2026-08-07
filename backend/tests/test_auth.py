def test_signup_allowed_roles(client):
    response = client.post(
        "/api/auth/signup",
        json={"name": "New User", "email": "new@test.com", "password": "password123", "role": "viewer"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "viewer"


def test_signup_blocked_admin_role(client):
    response = client.post(
        "/api/auth/signup",
        json={"name": "Fake Admin", "email": "fake@test.com", "password": "password123", "role": "admin"},
    )
    assert response.status_code == 403


def test_login_success(client, viewer_user):
    response = client.post(
        "/api/auth/login",
        data={"username": viewer_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_password(client, viewer_user):
    response = client.post(
        "/api/auth/login",
        data={"username": viewer_user.email, "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_me_endpoint(client, viewer_headers, viewer_user):
    response = client.get("/api/auth/me", headers=viewer_headers)
    assert response.status_code == 200
    assert response.json()["email"] == viewer_user.email

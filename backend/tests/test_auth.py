"""Authentication and authorization tests."""
from app.models.models import User, UserRole


def test_login_success_returns_token_and_user(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "admin@example.com"
    assert body["user"]["role"] == "admin"


def test_login_wrong_password(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert "Incorrect email or password" in resp.json()["detail"]


def test_login_unknown_email(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


def test_login_invalid_email_format(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "x"},
    )
    assert resp.status_code == 422  # validation error


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, auth_headers, admin_user):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@example.com"


def test_me_rejects_bad_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_change_password(client, auth_headers):
    resp = client.post(
        "/api/v1/auth/password",
        headers=auth_headers,
        json={"current_password": "Admin123!", "new_password": "NewStrong123"},
    )
    assert resp.status_code == 204, resp.text
    # Old password no longer works.
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
    )
    assert resp2.status_code == 401
    # New password works.
    resp3 = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "NewStrong123"},
    )
    assert resp3.status_code == 200


def test_change_password_wrong_current(client, auth_headers):
    resp = client.post(
        "/api/v1/auth/password",
        headers=auth_headers,
        json={"current_password": "nope", "new_password": "NewStrong123"},
    )
    assert resp.status_code == 400


def test_admin_only_users_list_forbidden_for_manager(client, manager_headers):
    resp = client.get("/api/v1/users", headers=manager_headers)
    assert resp.status_code == 403


def test_admin_can_list_users(client, auth_headers, admin_user, manager_user):
    resp = client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert "admin@example.com" in emails
    assert "manager@example.com" in emails


def test_admin_can_create_user(client, auth_headers):
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": "new.user@example.com",
            "full_name": "New User",
            "password": "StrongPass123",
            "role": "manager",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["email"] == "new.user@example.com"


def test_admin_cannot_create_duplicate_email(client, auth_headers, admin_user):
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": "admin@example.com",
            "full_name": "Dup",
            "password": "StrongPass123",
        },
    )
    assert resp.status_code == 409


def test_admin_cannot_delete_self(client, auth_headers, admin_user):
    resp = client.delete(f"/api/v1/users/{admin_user.id}", headers=auth_headers)
    assert resp.status_code == 400


def test_short_password_rejected(client, auth_headers):
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={"email": "short@example.com", "full_name": "Short", "password": "123"},
    )
    assert resp.status_code == 422

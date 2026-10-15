"""Client CRUD, validation, duplicate protection, and pagination tests."""


def _create_client(client, headers, **overrides):
    payload = {
        "name": "Acme Corp",
        "email": "acme@example.com",
        "phone": "+380 44 000 00 00",
        "status": "active",
        "segment": "smb",
    }
    payload.update(overrides)
    return client.post("/api/v1/clients", headers=headers, json=payload)


def test_create_client(client, auth_headers):
    resp = _create_client(client, auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Acme Corp"
    assert body["email"] == "acme@example.com"
    assert "id" in body


def test_create_client_requires_auth(client):
    resp = client.post(
        "/api/v1/clients",
        json={"name": "X", "email": "x@example.com"},
    )
    assert resp.status_code == 401


def test_create_client_invalid_email(client, auth_headers):
    resp = _create_client(client, auth_headers, email="not-valid")
    assert resp.status_code == 422


def test_create_client_missing_name(client, auth_headers):
    resp = client.post(
        "/api/v1/clients", headers=auth_headers, json={"email": "a@b.com"}
    )
    assert resp.status_code == 422


def test_duplicate_email_rejected(client, auth_headers):
    assert _create_client(client, auth_headers).status_code == 201
    resp = _create_client(client, auth_headers, name="Acme 2")
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_duplicate_email_case_insensitive(client, auth_headers):
    assert _create_client(client, auth_headers).status_code == 201
    resp = _create_client(client, auth_headers, email="ACME@EXAMPLE.COM")
    assert resp.status_code == 409


def test_get_client(client, auth_headers):
    created = _create_client(client, auth_headers).json()
    resp = client.get(f"/api/v1/clients/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_client_not_found(client, auth_headers):
    resp = client.get("/api/v1/clients/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_update_client(client, auth_headers):
    created = _create_client(client, auth_headers).json()
    resp = client.patch(
        f"/api/v1/clients/{created['id']}",
        headers=auth_headers,
        json={"name": "Acme Renamed", "status": "vip"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme Renamed"
    assert resp.json()["status"] == "vip"


def test_update_client_email_conflict(client, auth_headers):
    a = _create_client(client, auth_headers, email="a@example.com").json()
    b = _create_client(client, auth_headers, name="B", email="b@example.com").json()
    resp = client.patch(
        f"/api/v1/clients/{b['id']}",
        headers=auth_headers,
        json={"email": "a@example.com"},
    )
    assert resp.status_code == 409


def test_delete_client(client, auth_headers):
    created = _create_client(client, auth_headers).json()
    resp = client.delete(f"/api/v1/clients/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204
    # Confirm gone.
    resp2 = client.get(f"/api/v1/clients/{created['id']}", headers=auth_headers)
    assert resp2.status_code == 404


def test_delete_client_not_found(client, auth_headers):
    resp = client.delete("/api/v1/clients/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_list_clients_pagination(client, auth_headers):
    for i in range(25):
        _create_client(client, auth_headers, name=f"Client {i}", email=f"c{i}@example.com")
    resp = client.get("/api/v1/clients?page=1&page_size=10", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 25
    assert len(body["items"]) == 10
    assert body["pages"] == 3
    assert body["page"] == 1

    resp2 = client.get("/api/v1/clients?page=3&page_size=10", headers=auth_headers)
    assert len(resp2.json()["items"]) == 5


def test_list_clients_search(client, auth_headers):
    _create_client(client, auth_headers, name="Zebra Ltd", email="zebra@example.com")
    _create_client(client, auth_headers, name="Alpha Inc", email="alpha@example.com")
    resp = client.get("/api/v1/clients?q=zebra", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Zebra Ltd"


def test_list_clients_filter_by_status(client, auth_headers):
    _create_client(client, auth_headers, name="A", email="a@example.com", status="active")
    _create_client(client, auth_headers, name="B", email="b@example.com", status="inactive")
    resp = client.get("/api/v1/clients?status=inactive", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "inactive"


def test_list_clients_sort(client, auth_headers):
    _create_client(client, auth_headers, name="Charlie", email="charlie@example.com")
    _create_client(client, auth_headers, name="Alpha", email="alpha@example.com")
    resp = client.get(
        "/api/v1/clients?sort_by=name&sort_dir=asc&page_size=10", headers=auth_headers
    )
    names = [i["name"] for i in resp.json()["items"]]
    assert names == sorted(names)


def test_empty_clients_list(client, auth_headers):
    resp = client.get("/api/v1/clients", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["pages"] == 0

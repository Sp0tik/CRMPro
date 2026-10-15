"""Deal CRUD, stage transitions, validation, and cascade tests."""
from app.models.models import Client, Deal, DealStage, Task


def _client(client, headers, email="deal-client@example.com"):
    resp = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"name": "Deal Client", "email": email, "status": "active"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_deal(client, headers, client_id, **overrides):
    payload = {"title": "Big deal", "client_id": client_id, "amount": 10000}
    payload.update(overrides)
    return client.post("/api/v1/deals", headers=headers, json=payload)


def test_create_deal(client, auth_headers):
    cid = _client(client, auth_headers)
    resp = _create_deal(client, auth_headers, cid)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Big deal"
    assert body["stage"] == "qualification"
    assert float(body["amount"]) == 10000


def test_create_deal_invalid_client(client, auth_headers):
    resp = _create_deal(client, auth_headers, client_id=99999)
    assert resp.status_code == 400
    assert "client_id" in resp.json()["detail"]


def test_create_deal_negative_amount(client, auth_headers):
    cid = _client(client, auth_headers)
    resp = _create_deal(client, auth_headers, cid, amount=-5)
    assert resp.status_code == 422


def test_change_stage_to_won_sets_probability(client, auth_headers):
    cid = _client(client, auth_headers)
    deal = _create_deal(client, auth_headers, cid, probability=30).json()
    resp = client.put(
        f"/api/v1/deals/{deal['id']}/stage",
        headers=auth_headers,
        json={"stage": "won"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage"] == "won"
    assert body["probability"] == 100


def test_change_stage_to_lost_records_reason(client, auth_headers):
    cid = _client(client, auth_headers)
    deal = _create_deal(client, auth_headers, cid).json()
    resp = client.put(
        f"/api/v1/deals/{deal['id']}/stage",
        headers=auth_headers,
        json={"stage": "lost", "loss_reason": "Price too high"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage"] == "lost"
    assert body["probability"] == 0
    assert body["loss_reason"] == "Price too high"


def test_stage_change_logs_activity(client, auth_headers, db_session):
    cid = _client(client, auth_headers)
    deal = _create_deal(client, auth_headers, cid).json()
    client.put(
        f"/api/v1/deals/{deal['id']}/stage",
        headers=auth_headers,
        json={"stage": "won"},
    )
    from app.models.models import Activity

    activities = db_session.query(Activity).filter(Activity.client_id == cid).all()
    types = [a.type for a in activities]
    assert "deal_created" in types
    assert "deal_won" in types


def test_update_deal(client, auth_headers):
    cid = _client(client, auth_headers)
    deal = _create_deal(client, auth_headers, cid).json()
    resp = client.patch(
        f"/api/v1/deals/{deal['id']}",
        headers=auth_headers,
        json={"title": "Renamed", "amount": 25000},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Renamed"
    assert float(resp.json()["amount"]) == 25000


def test_delete_deal(client, auth_headers):
    cid = _client(client, auth_headers)
    deal = _create_deal(client, auth_headers, cid).json()
    resp = client.delete(f"/api/v1/deals/{deal['id']}", headers=auth_headers)
    assert resp.status_code == 204


def test_delete_client_cascades_deals(client, auth_headers, db_session):
    cid = _client(client, auth_headers, email="cascade@example.com")
    _create_deal(client, auth_headers, cid, title="D1")
    _create_deal(client, auth_headers, cid, title="D2")
    assert db_session.query(Deal).filter(Deal.client_id == cid).count() == 2
    resp = client.delete(f"/api/v1/clients/{cid}", headers=auth_headers)
    assert resp.status_code == 204
    assert db_session.query(Deal).filter(Deal.client_id == cid).count() == 0


def test_list_deals_filter_by_stage(client, auth_headers):
    cid = _client(client, auth_headers)
    _create_deal(client, auth_headers, cid, title="A", stage="won")
    _create_deal(client, auth_headers, cid, title="B", stage="qualification")
    resp = client.get("/api/v1/deals?stage=won", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["stage"] == "won"


def test_list_deals_search_by_client(client, auth_headers):
    cid = _client(client, auth_headers, email="searchable@example.com")
    _create_deal(client, auth_headers, cid, title="UniqueTitleXYZ")
    resp = client.get("/api/v1/deals?q=UniqueTitle", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_empty_deals_list(client, auth_headers):
    resp = client.get("/api/v1/deals", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

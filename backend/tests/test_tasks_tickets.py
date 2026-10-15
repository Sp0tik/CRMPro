"""Task and ticket CRUD / relationship / status tests."""
from datetime import date, timedelta

from app.models.models import DealStage


def _client(client, headers, email="task-client@example.com"):
    resp = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"name": "Task Client", "email": email, "status": "active"},
    )
    return resp.json()["id"]


def _create_task(client, headers, **overrides):
    payload = {"title": "Follow up", "priority": "medium", "status": "todo"}
    payload.update(overrides)
    return client.post("/api/v1/tasks", headers=headers, json=payload)


def test_create_task(client, auth_headers):
    cid = _client(client, auth_headers)
    resp = _create_task(client, auth_headers, client_id=cid)
    assert resp.status_code == 201, resp.text
    assert resp.json()["title"] == "Follow up"


def test_create_task_linked_to_deal(client, auth_headers):
    cid = _client(client, auth_headers, email="deal-link@example.com")
    deal = client.post(
        "/api/v1/deals",
        headers=auth_headers,
        json={"title": "Deal", "client_id": cid, "amount": 100},
    ).json()
    resp = _create_task(client, auth_headers, deal_id=deal["id"])
    assert resp.status_code == 201
    assert resp.json()["deal_id"] == deal["id"]


def test_create_task_invalid_deal(client, auth_headers):
    resp = _create_task(client, auth_headers, deal_id=99999)
    assert resp.status_code == 400


def test_update_task_status(client, auth_headers):
    task = _create_task(client, auth_headers).json()
    resp = client.patch(
        f"/api/v1/tasks/{task['id']}",
        headers=auth_headers,
        json={"status": "done"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_task_filters(client, auth_headers):
    today = date.today()
    _create_task(client, auth_headers, title="Today", due_date=str(today))
    _create_task(
        client, auth_headers, title="Overdue",
        due_date=str(today - timedelta(days=3)),
    )
    _create_task(
        client, auth_headers, title="Future",
        due_date=str(today + timedelta(days=5)),
    )
    _create_task(
        client, auth_headers, title="Done", status="done", due_date=str(today)
    )

    today_resp = client.get("/api/v1/tasks?filter=today", headers=auth_headers)
    assert {t["title"] for t in today_resp.json()["items"]} == {"Today"}

    overdue_resp = client.get("/api/v1/tasks?filter=overdue", headers=auth_headers)
    assert {t["title"] for t in overdue_resp.json()["items"]} == {"Overdue"}

    upcoming_resp = client.get("/api/v1/tasks?filter=upcoming", headers=auth_headers)
    assert {t["title"] for t in upcoming_resp.json()["items"]} == {"Future"}

    done_resp = client.get("/api/v1/tasks?filter=done", headers=auth_headers)
    assert {t["title"] for t in done_resp.json()["items"]} == {"Done"}


def test_delete_task(client, auth_headers):
    task = _create_task(client, auth_headers).json()
    resp = client.delete(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 204


def test_ticket_lifecycle(client, auth_headers):
    cid = _client(client, auth_headers, email="ticket@example.com")
    ticket = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={"title": "Cannot login", "client_id": cid, "priority": "high"},
    ).json()
    assert ticket["status"] == "open"

    # Add a message -> moves to in_progress.
    msg = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        headers=auth_headers,
        json={"body": "Looking into it."},
    )
    assert msg.status_code == 201

    updated = client.get(f"/api/v1/tickets/{ticket['id']}", headers=auth_headers).json()
    assert updated["status"] == "in_progress"
    assert len(updated["messages"]) == 1


def test_cannot_reply_to_closed_ticket(client, auth_headers):
    cid = _client(client, auth_headers, email="closed@example.com")
    ticket = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={"title": "Issue", "client_id": cid},
    ).json()
    client.put(
        f"/api/v1/tickets/{ticket['id']}/status",
        headers=auth_headers,
        json={"status": "closed"},
    )
    resp = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        headers=auth_headers,
        json={"body": "Reopen please"},
    )
    assert resp.status_code == 400


def test_closing_ticket_sets_closed_at(client, auth_headers):
    cid = _client(client, auth_headers, email="closed2@example.com")
    ticket = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={"title": "Issue", "client_id": cid},
    ).json()
    resp = client.put(
        f"/api/v1/tickets/{ticket['id']}/status",
        headers=auth_headers,
        json={"status": "closed"},
    )
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is not None


def test_delete_ticket(client, auth_headers):
    cid = _client(client, auth_headers, email="del@example.com")
    ticket = client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={"title": "Issue", "client_id": cid},
    ).json()
    resp = client.delete(f"/api/v1/tickets/{ticket['id']}", headers=auth_headers)
    assert resp.status_code == 204

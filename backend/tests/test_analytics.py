"""Analytics / dashboard calculation tests."""
from datetime import date, timedelta


def _seed_pipeline(client, headers):
    """Create one client with a mix of deals for deterministic math."""
    c = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"name": "Analytics Co", "email": "analytics@example.com", "status": "active"},
    ).json()
    cid = c["id"]
    # open deal (pipeline)
    client.post(
        "/api/v1/deals", headers=headers,
        json={"title": "Open", "client_id": cid, "amount": 100000, "stage": "negotiation",
              "probability": 50},
    )
    # won deal (recognised revenue)
    client.post(
        "/api/v1/deals", headers=headers,
        json={"title": "Won", "client_id": cid, "amount": 80000, "stage": "won"},
    )
    # lost deal (never revenue)
    client.post(
        "/api/v1/deals", headers=headers,
        json={"title": "Lost", "client_id": cid, "amount": 50000, "stage": "lost"},
    )
    return cid


def test_dashboard_empty_database(client, auth_headers):
    resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["clients_total"] == 0
    assert body["deals_total"] == 0
    assert body["open_revenue"] == 0
    assert body["won_revenue"] == 0
    assert body["win_rate"] == 0
    assert body["recent_deals"] == []


def test_dashboard_revenue_split(client, auth_headers):
    _seed_pipeline(client, auth_headers)
    body = client.get("/api/v1/analytics/dashboard", headers=auth_headers).json()

    assert body["clients_total"] == 1
    assert body["deals_total"] == 3
    assert body["deals_active"] == 1  # negotiation
    assert body["deals_won"] == 1
    assert body["deals_lost"] == 1

    # Open pipeline = only the open deal (100000), NOT the won/lost ones.
    assert body["open_revenue"] == 100000
    # Recognised revenue = only the won deal.
    assert body["won_revenue"] == 80000
    # Weighted pipeline = 100000 * 50% = 50000.
    assert body["weighted_pipeline"] == 50000
    # win rate = won / (won + lost) = 1/2 = 50%.
    assert body["win_rate"] == 50.0


def test_report_stages_and_managers(client, auth_headers):
    _seed_pipeline(client, auth_headers)
    body = client.get("/api/v1/analytics/report", headers=auth_headers).json()

    stages = {s["stage"]: s for s in body["stages"]}
    assert stages["won"]["count"] == 1
    assert stages["won"]["amount"] == 80000
    assert stages["lost"]["count"] == 1
    assert stages["negotiation"]["count"] == 1

    # Manager performance contains the admin who created the deals.
    assert len(body["managers"]) >= 1
    admin = next(m for m in body["managers"] if m["manager_name"] == "Test Admin")
    assert admin["deals_won"] == 1
    assert admin["won_amount"] == 80000


def test_report_trend_populated(client, auth_headers):
    _seed_pipeline(client, auth_headers)
    body = client.get("/api/v1/analytics/report", headers=auth_headers).json()
    assert len(body["trend"]) >= 1
    current_month = date.today().strftime("%Y-%m")
    point = next(t for t in body["trend"] if t["period"] == current_month)
    assert point["deals_created"] == 3
    assert point["deals_won"] == 1
    assert point["deals_lost"] == 1


def test_report_period_filter(client, auth_headers):
    _seed_pipeline(client, auth_headers)
    # A window in the future should exclude today's deals.
    future = (date.today() + timedelta(days=30)).isoformat()
    body = client.get(
        f"/api/v1/analytics/report?date_from={future}", headers=auth_headers
    ).json()
    assert body["kpis"]  # present
    deals_created = next(k for k in body["kpis"] if k["key"] == "deals_created")
    assert deals_created["value"] == 0


def test_export_csv(client, auth_headers):
    _seed_pipeline(client, auth_headers)
    resp = client.get("/api/v1/analytics/export.csv", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    text = resp.text
    assert "CRMPro Analytics Report" in text
    assert "Stage" in text
    assert "Manager" in text


def test_analytics_requires_auth(client):
    resp = client.get("/api/v1/analytics/dashboard")
    assert resp.status_code == 401

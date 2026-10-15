"""Live smoke test for CRMPro — 15 checks against a running server.

Usage:  python _smoke_live.py [base_url]   (default http://127.0.0.1:8000)
Exits 0 only when all 15 checks pass.
"""
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ADMIN = {"email": "admin@crmpro.example", "password": "Admin123!"}

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    c = httpx.Client(base_url=BASE, timeout=10.0)

    # 1. Health
    r = c.get("/api/health")
    check("01 GET /api/health -> 200 ok",
          r.status_code == 200 and r.json().get("status") == "ok", r.text[:80])

    # 2. DB health
    r = c.get("/api/health/db")
    check("02 GET /api/health/db -> 200 reachable",
          r.status_code == 200 and r.json().get("database") == "reachable", r.text[:80])

    # 3. SPA entry
    r = c.get("/")
    check("03 GET / -> 200 HTML SPA",
          r.status_code == 200 and "html" in r.headers.get("content-type", ""), r.headers.get("content-type", ""))

    # 4. Static asset
    r = c.get("/static/js/app.js")
    check("04 GET /static/js/app.js -> 200",
          r.status_code == 200 and len(r.text) > 100, f"{r.status_code} len={len(r.text)}")

    # 5. OpenAPI docs
    r = c.get("/api/docs")
    check("05 GET /api/docs -> 200",
          r.status_code == 200, str(r.status_code))

    # 6. Login with wrong password
    r = c.post("/api/v1/auth/login", json={"email": ADMIN["email"], "password": "nope"})
    check("06 login wrong password -> 401", r.status_code == 401, str(r.status_code))

    # 7. Login OK
    r = c.post("/api/v1/auth/login", json=ADMIN)
    token = r.json().get("access_token") if r.status_code == 200 else None
    check("07 login admin -> 200 + token", r.status_code == 200 and token, str(r.status_code))
    if not token:
        for name, _, _ in results:
            pass
        finish()
    auth = {"Authorization": f"Bearer {token}"}

    # 8. /auth/me
    r = c.get("/api/v1/auth/me", headers=auth)
    check("08 GET /auth/me -> 200 role=admin",
          r.status_code == 200 and r.json().get("role") == "admin", r.text[:80])

    # 9. Unauthenticated clients list
    r = c.get("/api/v1/clients")
    check("09 GET /clients unauth -> 401", r.status_code == 401, str(r.status_code))

    # 10. Seeded clients list
    r = c.get("/api/v1/clients", headers=auth)
    total = r.json().get("total", 0) if r.status_code == 200 else -1
    check("10 GET /clients auth -> 200, total >= 5 (seeded)",
          r.status_code == 200 and total >= 5, f"total={total}")

    # 11. Create client
    r = c.post("/api/v1/clients", headers=auth,
               json={"name": "Smoke Test Ltd", "email": "smoke@example.com",
                     "status": "active", "segment": "smb"})
    cid = r.json().get("id") if r.status_code == 201 else None
    check("11 POST /clients -> 201", r.status_code == 201 and cid, str(r.status_code))

    # 12. Update client
    if cid:
        r = c.patch(f"/api/v1/clients/{cid}", headers=auth,
                    json={"name": "Smoke Test Renamed"})
        check("12 PATCH /clients/{id} -> 200",
              r.status_code == 200 and r.json().get("name") == "Smoke Test Renamed", str(r.status_code))
    else:
        check("12 PATCH /clients/{id} -> 200", False, "skipped: no client id")

    # 13. Delete client + verify gone
    if cid:
        r1 = c.delete(f"/api/v1/clients/{cid}", headers=auth)
        r2 = c.get(f"/api/v1/clients/{cid}", headers=auth)
        check("13 DELETE /clients/{id} -> 204 then 404",
              r1.status_code == 204 and r2.status_code == 404,
              f"{r1.status_code}/{r2.status_code}")
    else:
        check("13 DELETE /clients/{id} -> 204 then 404", False, "skipped")

    # 14. Deals list (seeded pipeline)
    r = c.get("/api/v1/deals", headers=auth)
    check("14 GET /deals -> 200", r.status_code == 200 and "total" in r.json(),
          str(r.status_code))

    # 15. Analytics dashboard
    r = c.get("/api/v1/analytics/dashboard", headers=auth)
    check("15 GET /analytics/dashboard -> 200",
          r.status_code == 200 and isinstance(r.json(), dict), str(r.status_code))

    finish()


def finish():
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\nSMOKE RESULT: {passed}/{total} passed")
    sys.exit(0 if passed == total and total == 15 else 1)


if __name__ == "__main__":
    main()

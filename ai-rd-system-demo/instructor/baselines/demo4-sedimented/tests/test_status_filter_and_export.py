from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_status_filter_exact_match():
    r = client.get("/api/financing-applications?status=APPROVED", headers={"X-User": "alice"})
    body = r.json()
    assert body["total"] == 2
    assert all(item["status"] == "APPROVED" for item in body["items"])


def test_combined_customer_and_status_filter():
    r = client.get(
        "/api/financing-applications?customer_name=%E5%8D%97%E6%B9%BE&status=SUBMITTED",
        headers={"X-User": "bob"},
    )
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "FA-2002"


def test_status_filter_empty_result():
    r = client.get("/api/financing-applications?status=WITHDRAWN", headers={"X-User": "alice"})
    body = r.json()
    assert body["total"] == 0


def test_export_uses_current_filters_and_permission_scope():
    r = client.post(
        "/api/financing-applications/export?status=APPROVED",
        headers={"X-User": "alice"},
    )
    assert r.status_code == 200
    job = r.json()
    assert job["status"] == "QUEUED"
    payload = job["payload"]
    assert payload["filters"] == {"customer_name": None, "status": "APPROVED"}
    assert payload["requested_by"] == "alice"
    assert payload["tenant_scope"] == ["NORTH"]
    assert {row["id"] for row in payload["rows"]} == {"FA-1002", "FA-1005"}
    assert all(set(row.keys()) == {"id", "customer_name", "status", "amount"} for row in payload["rows"])

    fetched = client.get(f"/api/export-jobs/{job['id']}").json()
    assert fetched == job


def test_export_cannot_see_rows_outside_tenant_scope():
    r = client.post("/api/financing-applications/export", headers={"X-User": "bob"})
    payload = r.json()["payload"]
    assert payload["tenant_scope"] == ["SOUTH"]
    assert all(row["id"].startswith("FA-2") for row in payload["rows"])

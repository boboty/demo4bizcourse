from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rejected_is_still_queryable_in_the_list():
    r = client.get("/api/financing-applications?status=REJECTED", headers={"X-User": "alice"})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "FA-1004"


def test_rejected_status_filter_exports_zero_rows():
    r = client.post(
        "/api/financing-applications/export?status=REJECTED",
        headers={"X-User": "alice"},
    )
    payload = r.json()["payload"]
    assert payload["filters"]["status"] == "REJECTED"
    assert payload["rows"] == []


def test_submitted_is_still_queryable_but_not_exportable():
    listed = client.get("/api/financing-applications?status=SUBMITTED", headers={"X-User": "alice"}).json()
    assert listed["total"] == 1
    exported = client.post(
        "/api/financing-applications/export?status=SUBMITTED",
        headers={"X-User": "alice"},
    ).json()
    assert exported["payload"]["rows"] == []


def test_mixed_export_keeps_only_approved_and_funded():
    r = client.post("/api/financing-applications/export", headers={"X-User": "alice"})
    payload = r.json()["payload"]
    assert {row["id"] for row in payload["rows"]} == {"FA-1002", "FA-1003", "FA-1005"}
    assert all(row["status"] in {"APPROVED", "FUNDED"} for row in payload["rows"])


def test_tenant_scope_and_eligibility_both_hold_for_bob():
    r = client.post("/api/financing-applications/export", headers={"X-User": "bob"})
    payload = r.json()["payload"]
    assert payload["tenant_scope"] == ["SOUTH"]
    assert {row["id"] for row in payload["rows"]} == {"FA-2001", "FA-2003"}
    assert all(row["id"].startswith("FA-2") for row in payload["rows"])
    assert all(row["status"] in {"APPROVED", "FUNDED"} for row in payload["rows"])


def test_approved_only_filter_is_unaffected_by_the_fix():
    r = client.post(
        "/api/financing-applications/export?status=APPROVED",
        headers={"X-User": "alice"},
    )
    payload = r.json()["payload"]
    assert {row["id"] for row in payload["rows"]} == {"FA-1002", "FA-1005"}

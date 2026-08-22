from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_preserves_data_permission():
    north = client.get("/api/financing-applications", headers={"X-User": "alice"}).json()
    south = client.get("/api/financing-applications", headers={"X-User": "bob"}).json()
    assert north["total"] == 5
    assert south["total"] == 3
    assert all(item["tenant"] == "NORTH" for item in north["items"])
    assert all(item["tenant"] == "SOUTH" for item in south["items"])


def test_existing_pagination_contract():
    r = client.get("/api/financing-applications?page=2&page_size=2", headers={"X-User": "alice"})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_customer_name_filter_matches_substring_case_insensitive():
    r = client.get(
        "/api/financing-applications?customer_name=%E6%99%A8%E6%B5%B7",
        headers={"X-User": "alice"},
    )
    body = r.json()
    assert body["total"] == 2
    assert all("晨海" in item["customer_name"] for item in body["items"])


def test_customer_name_filter_empty_result():
    r = client.get(
        "/api/financing-applications?customer_name=%E4%B8%8D%E5%AD%98%E5%9C%A8",
        headers={"X-User": "alice"},
    )
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_customer_name_filter_respects_pagination_and_permission():
    r = client.get(
        "/api/financing-applications?customer_name=%E5%8D%97%E6%B9%BE&page=1&page_size=1",
        headers={"X-User": "bob"},
    )
    body = r.json()
    assert body["total"] == 2
    assert body["page_size"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["tenant"] == "SOUTH"

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_users_returns_requested_page(client: TestClient) -> None:
    response = client.get("/api/users", params={"page": 2, "page_size": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert [item["username"] for item in payload["items"]] == ["ann.ops"]


def test_list_users_applies_filters(client: TestClient) -> None:
    response = client.get(
        "/api/users",
        params={"username": "ANN", "status": "active"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["username"] for item in payload["items"]] == ["anna"]


def test_list_users_rejects_invalid_pagination(client: TestClient) -> None:
    response = client.get("/api/users", params={"page": 0, "page_size": 101})
    assert response.status_code == 422


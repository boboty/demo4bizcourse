"""项目自带最小 smoke 测试：只验证接口存在、HTTP 正常、返回结构完整。

刻意不校验任何业务取值（discount / finalAmount 的正确性）——按业务规则验证
这些字段的测试，应由课堂现场的 Codex Agent 自己设计生成。
"""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_calculate_endpoint_is_declared_in_openapi() -> None:
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json")
    assert schema.status_code == 200
    post = schema.json()["paths"]["/api/orders/calculate"]["post"]
    assert post is not None


def test_calculate_returns_expected_structure() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/calculate",
            json={"memberLevel": "GOLD", "amount": 1000},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"status", "discount", "finalAmount"}
    assert payload["status"] == "SUCCESS"
    assert isinstance(payload["discount"], int)
    assert isinstance(payload["finalAmount"], int)


def test_invalid_member_level_is_rejected() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/calculate",
            json={"memberLevel": "PLATINUM", "amount": 1000},
        )
    assert response.status_code == 422

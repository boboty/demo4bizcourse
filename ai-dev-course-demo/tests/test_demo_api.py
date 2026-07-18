"""课堂演示专用教学接口测试（/api/demo/users/export/*）。

这些接口只服务教学状态页，用真实 23 条样例数据（含空显示名称的
bob）验证故障可预测、可重复；正式 /api/users/export 不受影响见
tests/test_user_export_api.py。
"""

from collections.abc import Iterator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import create_app
from app.repositories.user_repository import InMemoryUserRepository
from app.services.user_export_service import USER_EXPORT_HEADERS


def read_rows(content: bytes) -> list[tuple[object, ...]]:
    worksheet = load_workbook(BytesIO(content), read_only=True).active
    return list(worksheet.values)


@pytest.fixture
def sample_client() -> Iterator[TestClient]:
    with TestClient(create_app(InMemoryUserRepository.with_sample_data())) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Stage 1：/api/demo/users/export/null-failure
# ---------------------------------------------------------------------------


def test_null_failure_default_export_succeeds(sample_client: TestClient) -> None:
    response = sample_client.get("/api/demo/users/export/null-failure")

    assert response.status_code == 200
    rows = read_rows(response.content)
    assert rows[0] == USER_EXPORT_HEADERS
    assert len(rows) == 24


def test_null_failure_bob_triggers_explainable_500(sample_client: TestClient) -> None:
    response = sample_client.get("/api/demo/users/export/null-failure", params={"username": "bob"})

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "空值" in detail
    assert "None" in detail
    assert "strip" in detail


def test_null_failure_empty_result_triggers_explainable_500(sample_client: TestClient) -> None:
    response = sample_client.get(
        "/api/demo/users/export/null-failure", params={"username": "zzz_no_such_user"}
    )

    assert response.status_code == 500
    assert "空结果" in response.json()["detail"]


def test_null_failure_non_empty_display_name_still_succeeds(sample_client: TestClient) -> None:
    response = sample_client.get("/api/demo/users/export/null-failure", params={"username": "alice"})

    assert response.status_code == 200
    rows = read_rows(response.content)
    assert rows[1][1] == "alice"


# ---------------------------------------------------------------------------
# Stage 2：/api/demo/users/export/page-only
# ---------------------------------------------------------------------------


def test_page_only_exports_only_current_page(sample_client: TestClient) -> None:
    response = sample_client.get(
        "/api/demo/users/export/page-only", params={"page": 1, "page_size": 8}
    )

    assert response.status_code == 200
    rows = read_rows(response.content)
    assert rows[0] == USER_EXPORT_HEADERS
    assert [row[0] for row in rows[1:]] == list(range(1, 9))


def test_page_only_second_page_contains_only_second_page_data(sample_client: TestClient) -> None:
    response = sample_client.get(
        "/api/demo/users/export/page-only", params={"page": 2, "page_size": 8}
    )

    rows = read_rows(response.content)
    assert [row[0] for row in rows[1:]] == list(range(9, 17))


def test_page_only_does_not_export_full_filtered_result(sample_client: TestClient) -> None:
    response = sample_client.get(
        "/api/demo/users/export/page-only",
        params={"status": "active", "page": 1, "page_size": 8},
    )

    list_response = sample_client.get(
        "/api/users", params={"status": "active", "page": 1, "page_size": 100}
    )
    total_active = list_response.json()["total"]

    rows = read_rows(response.content)
    assert total_active > len(rows) - 1


def test_page_only_null_display_name_does_not_error(sample_client: TestClient) -> None:
    response = sample_client.get("/api/demo/users/export/page-only", params={"username": "bob"})

    assert response.status_code == 200
    rows = read_rows(response.content)
    assert rows[1][2] is None


def test_page_only_empty_result_is_valid_header_only_file(sample_client: TestClient) -> None:
    response = sample_client.get(
        "/api/demo/users/export/page-only", params={"username": "zzz_no_such_user"}
    )

    assert response.status_code == 200
    assert read_rows(response.content) == [USER_EXPORT_HEADERS]


# ---------------------------------------------------------------------------
# 正式接口未被教学故障污染
# ---------------------------------------------------------------------------


def test_formal_export_endpoint_unaffected_by_demo_endpoints(sample_client: TestClient) -> None:
    # 先触发教学故障，再确认正式接口仍然正确
    sample_client.get("/api/demo/users/export/null-failure", params={"username": "bob"})

    response = sample_client.get("/api/users/export", params={"username": "bob"})

    assert response.status_code == 200
    rows = read_rows(response.content)
    assert rows[1][1] == "bob"
    assert rows[1][2] is None

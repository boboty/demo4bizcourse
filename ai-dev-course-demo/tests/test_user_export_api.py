from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.api.users import EXCEL_MEDIA_TYPE
from app.services.user_export_service import USER_EXPORT_HEADERS


def read_rows(content: bytes) -> list[tuple[object, ...]]:
    worksheet = load_workbook(BytesIO(content), read_only=True).active
    return list(worksheet.values)


def test_export_response_is_an_excel_attachment(client: TestClient) -> None:
    response = client.get("/api/users/export", params={"status": "active"})

    assert response.status_code == 200
    assert response.headers["content-type"] == EXCEL_MEDIA_TYPE
    assert response.headers["content-disposition"] == 'attachment; filename="users.xlsx"'


def test_export_uses_chinese_headers_in_required_order(client: TestClient) -> None:
    response = client.get("/api/users/export", params={"status": "active"})

    rows = read_rows(response.content)
    assert rows[0] == USER_EXPORT_HEADERS
    assert rows[1] == (
        10,
        "anna",
        "Anna 安",
        "anna@example.com",
        "active",
        "2024-05-01 08:00:00",
    )


def test_empty_export_contains_headers_and_no_data_rows(client: TestClient) -> None:
    response = client.get("/api/users/export", params={"username": "missing"})

    assert response.status_code == 200
    assert read_rows(response.content) == [USER_EXPORT_HEADERS]


def test_null_display_name_is_an_empty_excel_cell(client: TestClient) -> None:
    response = client.get("/api/users/export", params={"username": "ann.ops"})

    assert response.status_code == 200
    exported_user = read_rows(response.content)[1]
    assert exported_user[1] == "ann.ops"
    # openpyxl 将写入的空字符串回读为 None，二者都表示空单元格。
    assert exported_user[2] is None


def test_export_and_list_share_filter_semantics(client: TestClient) -> None:
    params = {"username": "ANN", "status": "active"}
    list_response = client.get("/api/users", params=params)
    export_response = client.get("/api/users/export", params=params)

    list_ids = [item["id"] for item in list_response.json()["items"]]
    export_ids = [row[0] for row in read_rows(export_response.content)[1:]]
    assert export_ids == list_ids == [10]

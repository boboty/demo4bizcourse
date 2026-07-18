from fastapi.testclient import TestClient


def test_demo_users_page_returns_200(client: TestClient) -> None:
    response = client.get("/demo/users")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_demo_users_page_contains_key_elements(client: TestClient) -> None:
    html = client.get("/demo/users").text

    # 标题与副标题
    assert "用户列表演示" in html
    assert "AI 研发闭环课堂 Demo" in html
    # 筛选区：用户名、状态、查询、重置、导出
    assert 'id="filter-username"' in html
    assert 'id="filter-status"' in html
    assert 'id="btn-search"' in html
    assert 'id="btn-reset"' in html
    assert 'id="btn-export"' in html
    # 页面复用现有列表与导出 API，且不依赖外部 CDN
    assert "/api/users" in html
    assert "/api/users/export" in html
    assert "http://" not in html.replace("http://127.0.0.1", "")
    assert "https://" not in html
    # 请求详情区域默认折叠
    assert 'id="request-info"' in html
    assert "<details" in html
    # 本地 favicon，避免 /favicon.ico 404
    assert 'rel="icon"' in html

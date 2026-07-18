from fastapi.testclient import TestClient

STATE_PATHS = [
    "/demo/users/base",
    "/demo/users/null-failure",
    "/demo/users/page-only",
    "/demo/users/final",
]


def test_root_redirects_to_demo_nav(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/demo"


def test_root_redirect_target_is_reachable(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "AI研发验证闭环课堂演示" in response.text


def test_demo_nav_page_returns_200(client: TestClient) -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_demo_nav_page_contains_four_entries_and_route(client: TestClient) -> None:
    html = client.get("/demo").text

    assert "AI研发验证闭环课堂演示" in html
    assert "从一句模糊需求，到可以被证据证明的最终结果" in html
    for path in STATE_PATHS:
        assert f'href="{path}"' in html
    for phase in ["需求未实现", "功能出现但边界失败", "测试通过但目标未达", "目标与证据闭环"]:
        assert phase in html
    # 讲师说明默认折叠且不进后端
    assert 'id="instructor-guide"' in html
    assert "sessionStorage" in html


def test_demo_nav_page_distinguishes_demo1_and_demo2(client: TestClient) -> None:
    html = client.get("/demo").text

    assert "Demo 1 · 从模糊需求到可验证任务" in html
    assert "Demo 2 · 完整任务包驱动研发闭环" in html
    assert 'href="/demo/codex-loop"' in html
    # Demo 1 的四个入口选择器不应混入 Demo 2 的大入口卡
    assert html.count('class="card-enter"') == 4


def test_demo_users_redirects_to_final(client: TestClient) -> None:
    response = client.get("/demo/users", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/demo/users/final"


def test_demo_users_redirect_target_is_reachable(client: TestClient) -> None:
    response = client.get("/demo/users")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_unknown_demo_state_returns_404(client: TestClient) -> None:
    response = client.get("/demo/users/does-not-exist")

    assert response.status_code == 404


def test_all_four_state_pages_return_200_and_share_core_elements(client: TestClient) -> None:
    for path in STATE_PATHS:
        response = client.get(path)
        html = response.text

        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html")
        # 四状态共用核心列表能力：筛选、查询、重置、导出、请求详情
        assert 'id="filter-username"' in html
        assert 'id="filter-status"' in html
        assert 'id="btn-search"' in html
        assert 'id="btn-reset"' in html
        assert 'id="btn-export"' in html
        assert 'id="request-info"' in html
        assert 'id="stage-badge"' in html
        assert 'id="nav-prev"' in html
        assert 'id="nav-next"' in html
        assert 'id="instructor-guide"' in html
        assert 'href="/demo"' in html
        # 无外部 CDN 依赖
        assert "http://" not in html.replace("http://127.0.0.1", "")
        assert "https://" not in html


def test_state_page_declares_all_four_states_in_order(client: TestClient) -> None:
    html = client.get("/demo/users/base").text

    assert '"base"' in html and '"null-failure"' in html and '"page-only"' in html and '"final"' in html
    assert html.index('"base"') < html.index('"null-failure"') < html.index('"page-only"') < html.index('"final"')

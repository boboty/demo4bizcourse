from pathlib import Path

from fastapi.testclient import TestClient


SCENARIOS = [
    "knowledge-answer",
    "batch-workflow",
    "exception-agent",
    "independent-validation",
    "month-close",
]

STATIC_RESOURCES = [
    "shared/theme.css",
    "shared/components.css",
    "shared/demo-controller.js",
    "shared/instructor-guide.js",
    "shared/scenario-data.js",
    "index.html",
    *[f"scenarios/{scenario}.html" for scenario in SCENARIOS],
]


def test_health_and_overview(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/demo"
    overview = client.get("/demo")
    assert overview.status_code == 200
    assert "五个演示入口" in overview.text
    assert overview.text.count("class=\"primary-link\"") == 5


def test_all_scenario_pages_and_unknown_route(client: TestClient) -> None:
    for scenario in SCENARIOS:
        response = client.get(f"/demo/{scenario}")
        assert response.status_code == 200, scenario
        assert response.headers["content-type"].startswith("text/html")
        assert 'data-fullscreen' in response.text
        assert 'id="btn-guide"' in response.text
        assert 'id="btn-prev"' in response.text
        assert 'id="btn-next"' in response.text
        assert 'id="btn-reset"' in response.text
        assert 'id="btn-final"' in response.text
        assert 'id="step-select"' in response.text
        assert "外部" not in response.text or "外部网络" in response.text
        assert "https://" not in response.text
    assert client.get("/demo/not-a-scenario").status_code == 404


def test_all_referenced_static_resources_are_reachable(client: TestClient) -> None:
    for resource in STATIC_RESOURCES:
        response = client.get(f"/static/{resource}")
        assert response.status_code == 200, resource
        assert response.content


def test_static_pages_have_no_external_resource_urls(client: TestClient) -> None:
    for resource in STATIC_RESOURCES:
        if not resource.endswith((".html", ".css", ".js")):
            continue
        body = client.get(f"/static/{resource}").text
        assert "https://" not in body, resource
        assert "http://" not in body, resource
        assert "cdn" not in body.lower(), resource


def test_scenario_specific_requirements_are_present(client: TestClient) -> None:
    knowledge = client.get("/demo/knowledge-answer").text
    assert "华远商贸有限公司" in knowledge
    assert "回答更准确了，但事情还没有往前推进" in knowledge

    batch = client.get("/demo/batch-workflow").text
    assert "40" in batch and "37" in batch and "3" in batch
    assert "查看异常流水如何处理" in batch

    exception = client.get("/demo/exception-agent").text
    for phrase in ("证据工作台", "自动处理已停止", "待人工确认", "未自动过账", "任务推进时间线"):
        assert phrase in exception
    assert "自动过账" in exception

    validation = client.get("/demo/independent-validation").text
    for phrase in ("renderTests", "validation.tests", "验收未通过", "业务规则理解错误"):
        assert phrase in validation

    close = client.get("/demo/month-close").text
    assert "确认开始结账" in close
    assert "确定性规则" in close


def test_project_does_not_include_old_project_files() -> None:
    project_root = Path(__file__).resolve().parents[1]
    assert project_root.name == "finance-agent-course-demo"
    assert not (project_root / "../ai-dev-course-demo/app/static/demo_users.html").resolve().is_relative_to(project_root)

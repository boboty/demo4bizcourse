from fastapi.testclient import TestClient


def test_codex_loop_page_returns_200(client: TestClient) -> None:
    response = client.get("/demo/codex-loop")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_codex_loop_page_contains_task_package(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert "任务：为用户列表增加 Excel 导出功能" in html
    assert "【任务目标】" in html
    assert "【功能要求】" in html
    assert "【技术约束】" in html
    assert "【验收标准】" in html
    assert "【验证要求】" in html
    assert "这次交给AI的，不再只是一句话" in html


def test_codex_loop_page_contains_seven_stages_in_order(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    titles = [
        "01 · 读取任务与项目",
        "02 · 制定计划",
        "03 · 实现功能",
        "04 · 建立验证证据",
        "05 · 运行自动化测试",
        "06 · 真实场景验证",
        "07 · 完成与证据映射",
    ]
    for title in titles:
        assert title in html

    # 阶段进度条（页面首次渲染即可见）按 01..07 顺序排列
    track_start = html.index('id="stage-track"')
    track_html = html[track_start : track_start + 2000]
    labels = ["读取任务与项目", "制定计划", "实现功能", "建立验证证据", "运行自动化测试", "真实场景验证", "完成与证据映射"]
    tracker_positions = [track_html.index(label) for label in labels]
    assert tracker_positions == sorted(tracker_positions)
    for index, label in enumerate(labels, start=1):
        assert f'data-stage="{index}"' in track_html

    # STAGES 配置（驱动执行顺序的唯一数据源）内部同样按 01..07 顺序声明
    script_start = html.index("<script>")
    script_html = html[script_start:]
    script_positions = [script_html.index(title) for title in titles]
    assert script_positions == sorted(script_positions)


def test_codex_loop_page_contains_playback_controls(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    for control_id in (
        "btn-start",
        "btn-pause",
        "btn-continue",
        "btn-step",
        "btn-jump-end",
        "btn-reset",
        "btn-reset-top",
    ):
        assert f'id="{control_id}"' in html


def test_codex_loop_page_shares_guide_preference_and_nav(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert 'id="instructor-guide"' in html
    assert "ai-demo.instructorNotes" in html
    assert 'href="/demo"' in html
    assert 'href="/demo/users/base"' in html
    # 无外部 CDN 依赖，不调用模型接口
    assert "http://" not in html.replace("http://127.0.0.1", "")
    assert "https://" not in html


def test_codex_loop_page_final_report_covers_ten_of_ten(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert "验收标准：10/10 已覆盖" in html
    assert 'id="final-report"' in html
    assert "hidden" in html  # 默认隐藏，需执行完成或跳转才显示


def test_codex_loop_page_contains_demo_comparison(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert 'id="comparison"' in html
    assert "模糊需求驱动" in html
    assert "完整任务包驱动" in html
    assert "问题不是AI不会写，而是工作没有被完整定义。" in html
    assert "不是省掉验证，而是避免验证到最后才发现目标定义不完整。" in html

from fastapi.testclient import TestClient

STAGE_TITLES = [
    "01 · 主代理读取任务包",
    "02 · 主代理制定执行计划",
    "03 · 主代理拉起代码子代理",
    "04 · 代码子代理完成实现",
    "05 · 主代理执行阶段门禁并驳回",
    "06 · 代码子代理补充验证",
    "07 · 主代理门禁放行",
    "08 · 独立验收代理最终验收",
]


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


def test_codex_loop_page_contains_eight_stages_in_order(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    for title in STAGE_TITLES:
        assert title in html

    # 阶段进度条（页面首次渲染即可见）按 01..08 顺序排列
    track_start = html.index('id="stage-track"')
    track_html = html[track_start : track_start + 2500]
    labels = ["读取任务包", "制定计划", "拉起子代理", "完成实现", "门禁驳回", "补充验证", "门禁放行", "最终验收"]
    tracker_positions = [track_html.index(label) for label in labels]
    assert tracker_positions == sorted(tracker_positions)
    for index, label in enumerate(labels, start=1):
        assert f'data-stage="{index}"' in track_html

    # STAGES 配置（驱动执行顺序的唯一数据源）内部同样按 01..08 顺序声明
    script_start = html.index("<script>")
    script_html = html[script_start:]
    script_positions = [script_html.index(title) for title in STAGE_TITLES]
    assert script_positions == sorted(script_positions)


def test_codex_loop_page_distinguishes_three_roles(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert "🧭 主代理" in html
    assert "🛠 代码子代理" in html
    assert "✅ 独立验收代理" in html
    # 角色协作流程静态图
    assert "角色协作流程" in html
    assert "派发任务" in html
    assert "驳回 / 放行" in html
    # 8 个节点各自标注了角色（main/sub/final），用于渲染时区分颜色
    assert 'role: "main"' in html
    assert 'role: "sub"' in html
    assert 'role: "final"' in html


def test_codex_loop_page_contains_gate_reject_and_pass(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert '"REJECTED"' in html
    assert '"PASSED"' in html
    assert "验证证据不足" in html
    assert "未运行全量测试" in html
    assert "阶段门禁未通过" in html
    assert "阶段门禁通过" in html
    assert "代码可能已经写对，但证据不够，主代理就不能放行。" in html
    assert "门禁不是阻止 AI 工作，而是决定证据够不够支撑下一步。" in html
    # 关键状态字符串（用于页面上的“当前状态”徽标）
    for status in ("READING", "PLANNING", "DELEGATED", "SUBMITTED",
                   "GATE REJECTED", "FIXING / VERIFYING", "GATE PASSED", "FINAL PASS"):
        assert status in html


def test_codex_loop_page_light_gap_is_not_a_bug(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert "尚未运行全量回归测试。" in html
    assert "25 passed in 0.42s" in html
    assert "5 passed in 0.31s" in html
    # 不应出现空值 Bug 或需求遗漏的旧 Demo1 式话术
    assert "AttributeError" not in html
    assert "IndexError" not in html


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


def test_codex_loop_page_final_report_covers_nine_of_nine(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert "验收项：9/9 已覆盖" in html
    assert 'id="final-report"' in html
    assert "hidden" in html  # 默认隐藏，需执行完成或跳转才显示
    for item in (
        "导出全部筛选结果", "中文列名正确", "空列表正常", "display_name 为空正常",
        "超过 10000 行返回 422", "复用已有筛选逻辑", "未改变原接口语义",
        "全量测试通过", "无越界修改",
    ):
        assert item in html


def test_codex_loop_page_keeps_four_key_takeaways(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert "主代理不必亲自执行每一步，但必须掌握计划、门禁和推进权。" in html
    assert "门禁不是让 AI 变慢，而是用低成本检查阻止高成本返工。" in html
    assert "执行完成不等于阶段通过；证据满足门禁，流程才能继续。" in html
    assert "最终验收仍然要回到原始目标，不能只接受执行者的完成声明。" in html
    assert "丝滑不是一路不停，" in html
    assert "而是任务定义清楚、分工明确、门禁有效，只在必要位置做一次低成本驳回。" in html


def test_codex_loop_page_contains_demo_comparison(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    assert 'id="comparison"' in html
    assert "模糊需求驱动" in html
    assert "完整任务包驱动" in html
    assert "问题不是AI不会写，而是工作没有被完整定义。" in html
    assert "门禁驳回（证据不足）" in html
    assert "独立验收 PASS" in html


def test_codex_loop_page_stage_delays_within_realistic_range(client: TestClient) -> None:
    html = client.get("/demo/codex-loop").text

    start = html.index("var STAGE_DELAYS_MS")
    end = html.index(";", start)
    array_text = html[start:end]
    delays = [int(token) for token in array_text.split("[", 1)[1].split("]")[0].split(",")]

    assert len(delays) == len(STAGE_TITLES)
    assert all(10_000 <= d <= 60_000 for d in delays)

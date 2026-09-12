"""Demo 3：任务级运行报表的每一条口径。

这一组测试守的是「报表里的数字可以被追溯到某条 run JSON」。课堂会指着
「Token / 任务 = 5,603.4」说事，所以每个派生量都必须由真实记录加出来，
样本筛选、状态判定、缓存处理都不许含糊。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.analytics import build_report
from app.config import ProviderConfig, runs_dir
from app.engine import RunEngine
from app.main import app
from app.models import RunRecord, StepRecord
from app.store import RunStore
from tests.conftest import FakeProvider

client = TestClient(app)
CONFIG = ProviderConfig(
    base_url="https://example.invalid/v1", api_key="test-key", model="fake-base"
)
SCENARIO = "tianjin-freight"


def step(number, *, status="ok", phase="parse", tools=0, model="m",
         input_tokens=10, output_tokens=5):
    return StepRecord(
        step=number, action=f"动作{number}", phase=phase, status=status, model=model,
        input_tokens=input_tokens, output_tokens=output_tokens, tool_calls=tools,
    )


def record(
    run_id="r1",
    *,
    mode="C",
    run_status="ok",
    steps=(),
    evidence_level="live",
    token_evidence="measured",
    input_tokens=100,
    output_tokens=50,
    cached_tokens=None,
    latency_ms=1000,
):
    return RunRecord(
        run_id=run_id,
        created_at="2026-09-12T00:00:00+00:00",
        scenario=SCENARIO,
        scenario_name="天津货代询价",
        mode=mode,
        mode_label=f"{mode} 档",
        request_text="测试",
        task="测试",
        steps=list(steps),
        evidence_level=evidence_level,
        token_evidence=token_evidence,
        usage={
            "model_calls": sum(1 for s in steps if s.model),
            "tool_calls": sum(s.tool_calls for s in steps),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "total_tokens": (
                input_tokens + output_tokens
                if input_tokens is not None and output_tokens is not None
                else None
            ),
            "latency_ms": latency_ms,
        },
        run_status=run_status,
    )


def items(layer, key="items"):
    return {item["key"]: item for item in layer[key]}


def layers_of(report):
    return {layer["key"]: layer for layer in report["layers"]}


# --------------------------------------------------------------------------
# 1 只读已有记录，不碰 provider
# --------------------------------------------------------------------------


def test_analytics_reads_saved_records_without_calling_the_provider(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(provider, CONFIG))
    client.post("/api/runs", json={"scenario": SCENARIO, "mode": "C"})
    calls_after_run = provider.call_count

    body = client.get("/api/analytics").json()

    assert provider.call_count == calls_after_run  # 聚合没有产生任何新调用
    assert body["source"] == "run_records"
    assert body["sample"]["total_records"] == 1


def test_the_endpoint_serves_the_same_numbers_the_module_computes(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    client.post("/api/runs", json={"scenario": SCENARIO, "mode": "C"})

    served = client.get("/api/analytics").json()
    direct = build_report(RunStore(runs_dir()).list_records())

    assert served["layers"] == direct["layers"]
    assert served["final"] == direct["final"]


def test_an_unknown_mode_is_rejected():
    assert client.get("/api/analytics?mode=Z").status_code == 400


def test_the_report_can_be_filtered_by_mode(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    client.post("/api/runs", json={"scenario": SCENARIO, "mode": "A"})
    client.post("/api/runs", json={"scenario": SCENARIO, "mode": "C"})

    all_modes = client.get("/api/analytics").json()
    c_only = client.get("/api/analytics?mode=c").json()

    assert all_modes["sample"]["valid_records"] == 2
    assert c_only["mode_filter"] == "C"
    assert c_only["sample"]["valid_records"] == 1
    # 按档筛选不改变总量的口径：只是换了一批样本。
    assert c_only["final"]["task_count"] == 1


# --------------------------------------------------------------------------
# 2 样本筛选：不完整的记录不混进统计
# --------------------------------------------------------------------------


def test_only_measured_and_live_records_enter_the_sample():
    records = [
        record("ok1"),
        record("structure", evidence_level="structure_only"),
        record("unmeasured", token_evidence="not_reported", input_tokens=None, output_tokens=None),
        record("partial", token_evidence="partial", input_tokens=None, output_tokens=None),
    ]
    report = build_report(records)

    assert report["sample"]["total_records"] == 4
    assert report["sample"]["valid_records"] == 1
    assert report["sample"]["excluded"]["structure_only"] == 1
    assert report["sample"]["excluded"]["token_incomplete"] == 2
    assert report["final"]["task_count"] == 1


def test_an_empty_sample_reports_dashes_not_zeros():
    report = build_report([])
    layer1 = items(layers_of(report)["layer1"])
    layer3 = items(layers_of(report)["layer3"])

    assert report["sample"]["valid_records"] == 0
    assert layer1["total_tokens"]["display"] == "—"
    assert layer1["avg_latency"]["display"] == "—"
    assert layer3["task_count"]["display"] == "0"
    assert layer3["tokens_per_task"]["display"] == "—"
    assert report["final"]["display_total_tokens"] == "—"
    assert report["example"] is None


# --------------------------------------------------------------------------
# 3 每一项的计算规则
# --------------------------------------------------------------------------


def test_task_count_is_one_per_valid_run_record():
    report = build_report([record("a"), record("b", mode="A"), record("c", mode="D")])
    assert items(layers_of(report)["layer3"])["task_count"]["value"] == 3


def test_total_tokens_sums_the_records_own_usage():
    # 两条记录：100+50 与 200+80。
    report = build_report([
        record("a", input_tokens=100, output_tokens=50),
        record("b", input_tokens=200, output_tokens=80),
    ])
    assert items(layers_of(report)["layer1"])["total_tokens"]["value"] == 430


def test_cached_tokens_are_never_added_into_the_total():
    report = build_report([
        record("a", input_tokens=100, output_tokens=50, cached_tokens=40),
        record("b", input_tokens=200, output_tokens=80, cached_tokens=10),
    ])
    layer1 = items(layers_of(report)["layer1"])
    layer2 = items(layers_of(report)["layer2"])

    assert layer1["total_tokens"]["value"] == 430          # 不是 480
    assert layer2["cached_tokens"]["value"] == 50          # 单独看，不并入
    assert layer2["input_tokens"]["value"] == 300


def test_cached_tokens_stay_unreported_when_no_record_has_them():
    report = build_report([record("a", cached_tokens=None)])
    assert items(layers_of(report)["layer2"])["cached_tokens"]["display"] == "未上报"


def test_per_task_metrics_divide_by_the_task_count():
    # 两次运行：3 次模型调用 / 1 次工具；1 次模型调用 / 2 次工具。
    first = record(
        "a", input_tokens=600, output_tokens=400,
        steps=(step(1), step(2, tools=1, phase="facts"), step(3)),
    )
    second = record(
        "b", input_tokens=200, output_tokens=100,
        steps=(step(1, tools=2, phase="facts"),),
    )
    layer3 = items(layers_of(build_report([first, second]))["layer3"])

    assert layer3["task_count"]["value"] == 2
    assert layer3["tokens_per_task"]["value"] == pytest.approx(650)      # (1000+300)/2
    assert layer3["model_calls_per_task"]["value"] == pytest.approx(2)   # (3+1)/2
    assert layer3["tool_calls_per_task"]["value"] == pytest.approx(1.5)  # (1+2)/2


def test_status_counts_and_rates():
    records = [
        record("ok", run_status="ok"),
        record("wait", run_status="waiting_human"),
        record("wait2", run_status="waiting_human"),
        record("bad", run_status="error"),
    ]
    report = build_report(records)
    status = items(layers_of(report)["layer3"], "status_items")

    assert status["completed"]["display"] == "1 件 / 25%"
    assert status["waiting_human"]["display"] == "2 件 / 50%"
    assert status["failed"]["display"] == "1 件 / 25%"
    assert items(layers_of(report)["layer1"])["error_runs"]["display"] == "1 次 / 25%"


def test_blocked_is_counted_from_steps_not_from_a_run_status():
    """run 级状态里没有 blocked：这一项按「有没有被阻塞的步骤」判定。"""
    records = [
        record("blocked", steps=(step(1), step(2, status="blocked", phase="facts"))),
        record("clean", steps=(step(1),)),
    ]
    status = items(layers_of(build_report(records))["layer3"], "status_items")

    assert status["blocked"]["value"] == 1
    assert "按步骤判定" in status["blocked"]["hint"]


def test_average_latency_is_the_run_level_total_not_a_single_call():
    records = [record("a", latency_ms=1000), record("b", latency_ms=3000)]
    layer1 = items(layers_of(build_report(records))["layer1"])

    assert layer1["avg_latency"]["value"] == 2000
    assert "run 级总耗时" in layer1["avg_latency"]["hint"]
    assert "不是单次模型调用" in layer1["avg_latency"]["hint"]


def test_structure_metrics_are_counts_not_a_complexity_score():
    records = [
        record("c", steps=(step(1, phase="parse"), step(2, phase="verify"))),
        record("d", steps=(step(1, phase="d-parse-1"), step(2, phase="d-verify-1"))),
    ]
    structure = items(layers_of(build_report(records))["layer3"], "structure_items")

    assert structure["steps_per_task"]["value"] == pytest.approx(2)
    # C 的 verify 与 D 的 d-verify-1 都算做了校验。
    assert structure["verify_share"]["display"] == "100%"
    note = layers_of(build_report(records))["layer3"]["structure_note"]
    assert "不是「任务复杂度」的数学分数" in note


def test_a_truncated_run_still_counts_its_real_tokens():
    """输出被截断说的是文字，不是 Token 计量——它照样是有效样本。"""
    truncated = record("cut", steps=(step(1),), run_status="waiting_human")
    truncated.output_evidence  # derived from steps; nothing to set here
    report = build_report([truncated])

    assert report["sample"]["valid_records"] == 1
    assert report["final"]["task_count"] == 1


# --------------------------------------------------------------------------
# 4 三层与收束画面
# --------------------------------------------------------------------------


def test_the_three_layers_are_ordered_and_add_up():
    report = build_report([record("a", steps=(step(1), step(2, phase="gaps")))])
    assert [layer["key"] for layer in report["layers"]] == [
        "layer1", "layer2", "layer3"
    ]
    # 同一个数在两层里必须一致：模型调用次数不是两套口径。
    assert [items(layer)["model_calls"]["value"] for layer in report["layers"][:2]] == [2, 2]


def test_the_first_layer_has_no_task_level_metric():
    layer1 = items(layers_of(build_report([record("a")]))["layer1"])
    assert set(layer1) == {"total_tokens", "model_calls", "avg_latency", "error_runs"}
    for forbidden in ("task_count", "tokens_per_task", "model_calls_per_task",
                      "tool_calls_per_task", "waiting_human"):
        assert forbidden not in layer1


def test_the_second_layer_has_no_final_matrix():
    report = build_report([record("a")])
    layer2 = items(layers_of(report)["layer2"])
    assert "tokens_per_task" not in layer2
    assert "task_count" not in layer2
    assert "formula" not in json.dumps(report["layers"][1], ensure_ascii=False)


def test_the_final_block_is_task_count_times_tokens_per_task():
    records = [
        record("a", input_tokens=300, output_tokens=100),
        record("b", input_tokens=600, output_tokens=200),
    ]
    final = build_report(records)["final"]

    assert final["task_count"] == 2
    assert final["tokens_per_task"] == pytest.approx(600)
    assert final["total_tokens"] == 1200
    assert final["display_task_count"] == "2"
    assert final["display_tokens_per_task"] == "600.0"
    assert final["display_total_tokens"] == "1,200"
    assert final["formula"] == "任务量 × 单任务 Token = Token 总量"
    assert "更多真实任务" in final["question"]


def test_the_example_is_the_newest_valid_run():
    older = record("old").model_copy(update={"created_at": "2026-09-01T00:00:00+00:00"})
    newer = record("new").model_copy(update={"created_at": "2026-09-10T00:00:00+00:00"})
    report = build_report([newer, older])

    assert report["example"]["run_id"] == "new"
    # 示例只可能来自有效样本。
    assert build_report([record("s", evidence_level="structure_only")])["example"] is None


# --------------------------------------------------------------------------
# 5 页面：三层逐步展开，前两层不提前泄底
# --------------------------------------------------------------------------


def test_the_page_ships_only_the_first_layer_visible():
    html = client.get("/").text

    for section_id in ("d3L2", "d3L3", "d3Final"):
        tag = html.split(f'id="{section_id}"')[1].split(">")[0]
        assert "hidden" in tag, section_id
    layer1 = html.split('id="d3L1"')[1].split(">")[0]
    assert "hidden" not in layer1


def test_the_page_reveals_layers_in_order_with_a_restart():
    html = client.get("/").text

    assert 'id="d3Next">展开调用结构</button>' in html
    assert 'id="d3Restart" hidden>重新演示</button>' in html
    script = html.split("<script>")[1]
    # 展开顺序：第一步给第二层，第二步给第三层与最终公式。
    assert "next.textContent = '展开调用结构'" in script
    assert "next.textContent = '展开任务指标'" in script
    assert "d3Show('d3L3', d3.stage >= 3, animate)" in script
    assert "d3Show('d3Final', d3.stage >= 3, animate)" in script


def test_the_final_formula_is_not_rendered_before_the_third_layer():
    """最终公式只写进 d3Formula，而它所在的那一块初始是隐藏的。"""
    html = client.get("/").text
    assert html.count('id="d3Formula"') == 1
    before = html.split('id="d3Formula"')[0]
    assert "任务量 × 单任务 Token" not in before

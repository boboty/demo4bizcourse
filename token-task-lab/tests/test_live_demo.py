"""Demo 1 的实时执行，以及 Demo 1 → Demo 2 是同一次运行。

课堂顺序是「先看到业务过程 → 再看到 Token 现象 → 最后解释机制」，所以这一组
测试守两件事：

1. Demo 1 的执行过程必须由真实 engine 推进，而且全程不出现任何 Token 字段；
2. Demo 1 跑出来的那条记录，就是 Demo 2 重放的那一条 —— 不是另跑一次。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import ProviderConfig
from app.engine import RunEngine
from app.main import app
from app.provider import ProviderResult
from app.store import RunStore
from tests.conftest import FakeProvider

client = TestClient(app)
CONFIG = ProviderConfig(
    base_url="https://example.invalid/v1", api_key="test-key", model="fake-base"
)


@pytest.fixture
def live_run(monkeypatch):
    """跑一次实时执行流，返回 (events, provider)。"""

    def _run(provider=None, mode="C", save=True):
        engine_provider = provider or FakeProvider()
        monkeypatch.setattr(
            "app.main._engine", lambda: RunEngine(engine_provider, CONFIG)
        )
        with client.stream(
            "POST",
            "/api/runs/stream",
            json={"scenario": "tianjin-freight", "mode": mode, "save": save},
        ) as response:
            assert response.status_code == 200, response.text
            assert response.headers["content-type"].startswith("application/x-ndjson")
            events = [
                json.loads(line) for line in response.iter_lines() if line.strip()
            ]
        return events, engine_provider

    return _run


def by_type(events, kind):
    return [event for event in events if event["type"] == kind]


def settled_steps(events) -> dict[int, dict]:
    """每一步的最终状态（工具步骤会被修订一次，后到的为准）。"""
    settled: dict[int, dict] = {}
    for event in by_type(events, "step"):
        settled[event["step"]] = event
    return settled


# --------------------------------------------------------------------------
# 1 执行过程由真实 engine 推进，且不泄露 Token
# --------------------------------------------------------------------------


def test_demo_1_live_stream_never_carries_a_token_field(live_run):
    events, _ = live_run()
    raw = json.dumps(events, ensure_ascii=False)

    for forbidden in (
        "input_tokens",
        "output_tokens",
        "cached_tokens",
        "total_tokens",
        "model_calls",
        "tool_calls",
        "latency_ms",
        "finish_reason",
        "truncated",
        "usage",
        "model",
    ):
        assert forbidden not in raw, forbidden


def test_the_plan_is_handed_over_before_anything_runs(live_run):
    events, _ = live_run()
    start = events[0]

    # 页面最先拿到的是「打算做什么」，不是任何结果。
    assert start["type"] == "start"
    assert [item["phase"] for item in start["plan"]] == [
        "parse",
        "gaps",
        "facts",
        "judge",
        "verify",
        "deliver",
    ]
    # 计划里只有步骤名，没有状态：完成 / 被阻塞 / 停下等人只能由真实执行填上。
    assert all(
        set(item) == {"step", "phase", "action", "running_label", "done_label"}
        for item in start["plan"]
    )


def test_every_step_is_announced_started_then_settled_by_the_engine(live_run):
    events, _ = live_run()

    started = [event["step"] for event in by_type(events, "step_start")]
    assert started == [1, 2, 3, 4, 5, 6]  # 每一步都是 engine 真的开始执行了

    settled = settled_steps(events)
    assert sorted(settled) == [1, 2, 3, 4, 5, 6]
    assert [event["phase"] for _, event in sorted(settled.items())] == [
        "parse",
        "gaps",
        "facts",
        "judge",
        "verify",
        "deliver",
    ]


def test_step_states_come_from_the_real_run_not_from_the_plan(live_run):
    """计划里没有状态；状态只能来自真实执行——包括这一步被阻塞。"""
    events, _ = live_run()
    settled = settled_steps(events)

    assert settled[3]["status"] == "blocked"
    assert settled[6]["status"] == "waiting_human"


def test_an_engine_step_that_starts_is_announced_before_it_settles(live_run):
    events, _ = live_run()
    kinds = [event["type"] for event in events]
    first_start = kinds.index("step_start")
    first_step = next(i for i, kind in enumerate(kinds) if kind == "step")

    assert first_start < first_step


# --------------------------------------------------------------------------
# 2 工具事实三态要能显示到 Demo 1
# --------------------------------------------------------------------------


def test_the_fact_step_carries_the_three_states_to_demo_1(live_run):
    events, _ = live_run()
    facts_event = settled_steps(events)[3]

    assert [(f["title"], f["state"], f["state_label"]) for f in facts_event["facts"]] == [
        ("查询船期", "unverified", "有结果但未核验"),
        ("查询运价", "missing", "无结果"),
        ("确认舱位", "missing", "无结果"),
    ]
    # 「拿到了 ≠ 能用」：船期有结果，这一步仍然是被阻塞的。
    assert facts_event["status"] == "blocked"


def test_the_last_step_reports_waiting_for_a_human(live_run):
    events, _ = live_run()
    assert settled_steps(events)[6]["status"] == "waiting_human"

    done = by_type(events, "done")[0]
    assert done["run_status"] == "waiting_human"
    assert done["saved"] is True


def test_a_failed_call_is_reported_instead_of_silently_ending(live_run):
    # 第 3 次模型调用是 judge（parse/gaps 之后、facts 是工具步骤），也就是记录里的第 4 步。
    events, _ = live_run(FakeProvider(fail_on_call=3))

    settled = settled_steps(events)
    assert settled[4]["status"] == "error"
    assert by_type(events, "done")[0]["run_status"] == "error"


# --------------------------------------------------------------------------
# 3 Demo 1 与 Demo 2 是同一次运行
# --------------------------------------------------------------------------


def test_the_live_run_id_is_the_replay_run_id(live_run, tmp_path):
    events, _ = live_run()
    run_id = by_type(events, "start")[0]["run_id"]

    # 同一个 run_id 一路走到底：done 事件、保存的记录、重放的记录。
    assert by_type(events, "done")[0]["run_id"] == run_id
    stored = client.get(f"/api/runs/{run_id}")
    assert stored.status_code == 200
    assert stored.json()["front"]["run_id"] == run_id

    replay = client.get(f"/api/runs/{run_id}/replay").json()
    assert replay["run_id"] == run_id
    assert replay["source"] == "run_record"
    assert [frame["phase"] for frame in replay["frames"]] == [
        event["phase"] for _, event in sorted(settled_steps(events).items())
    ]


def test_the_run_id_is_known_before_the_run_finishes(live_run):
    """页面在执行前就拿到 run_id —— 这正是两条 Demo 共用一次运行的前提。"""
    events, _ = live_run()
    assert by_type(events, "start")[0]["run_id"]
    assert by_type(events, "start")[0]["run_id"] == by_type(events, "done")[0]["run_id"]


def test_the_live_run_is_saved_so_demo_2_can_replay_it(live_run, tmp_path):
    events, _ = live_run()
    run_id = by_type(events, "done")[0]["run_id"]

    store = RunStore(tmp_path / "runs")
    assert store.path_for(run_id).is_file()


def test_the_live_run_keeps_the_c_chain_and_its_numbers(live_run):
    """实时视图只是多看了一眼，记录本身没有被改动。"""
    events, _ = live_run()
    run_id = by_type(events, "done")[0]["run_id"]
    back = client.get(f"/api/runs/{run_id}").json()["back"]

    assert [step["phase"] for step in back["steps"]] == [
        "parse",
        "gaps",
        "facts",
        "judge",
        "verify",
        "deliver",
    ]
    assert back["usage"]["model_calls"] == 5
    assert back["usage"]["tool_calls"] == 3
    assert back["token_evidence"] == "measured"


def test_the_stream_saves_nothing_when_saving_is_off(live_run, tmp_path):
    events, _ = live_run(save=False)
    assert by_type(events, "done")[0]["saved"] is False
    run_id = by_type(events, "done")[0]["run_id"]
    assert not RunStore(tmp_path / "runs").path_for(run_id).is_file()


def test_an_unknown_mode_is_rejected_before_anything_runs():
    response = client.post(
        "/api/runs/stream", json={"scenario": "tianjin-freight", "mode": "Z"}
    )
    assert response.status_code == 400
# --------------------------------------------------------------------------
# 4 第三讲的直接入口：不经过运行背面
# --------------------------------------------------------------------------


def test_the_page_offers_a_direct_replay_entry_from_demo_1():
    html = client.get("/").text

    assert 'id="replayFromDemo1"' in html
    assert "重放刚才这次任务的 Token" in html
    # 刷新 / 跨讲回来的入口，以及带 run_id 直接打开重放的 URL 参数。
    assert 'id="lastRunBar"' in html
    assert "params.get('replay')" in html


def test_the_replay_view_keeps_its_totals_hidden_until_the_end():
    html = client.get("/").text

    final_tag = html.split('id="replayFinal"')[1].split(">")[0]
    assert "hidden" in final_tag
    assert '<div class="totals" id="replayFinalNumbers"></div>' in html
    # 打开重放时不会先看到 Token 总量或调用次数：这些只在重放结束后写入。
    assert 'id="replayNumber"></div>' in html


def test_the_token_bearing_sections_start_collapsed():
    """实验对照与已保存记录都含 Token 明细，讲完 Demo 2 之前不该展开着。"""
    html = client.get("/").text

    assert html.count('<details class="sec">') == 2
    assert '<details class="sec" open>' not in html
    # 这两块分别是 A/B/C/D 对照表与已保存记录，都还在，只是收起来了。
    assert 'id="cmpWrap"' in html and 'id="records"' in html

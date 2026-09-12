"""Demo 2 的 Token 累计重放：逐帧数字必须来自记录本身。

课堂上要指着大号数字说「这就是这件任务长出来的 Token」，所以这一页的每一条
结论都要能被下面的测试挡住：

1. 重放绑定的就是 Demo 1 那一条 run_id，不是另跑一次。
2. 每一帧的累计值等于它前面所有模型步骤 input_tokens + output_tokens 的和。
3. 工具步骤真的不加 Token；缓存 Token 不会被重复加一遍。
4. Usage 不完整或输出被截断的记录，不能伪装成一次完整的课堂重放。
5. 重放不触发任何新的 provider 调用。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import ProviderConfig
from app.engine import RunEngine
from app.main import app
from app.views import FORBIDDEN_IN_FRONT
from tests.conftest import FakeProvider
from tests.test_course_invariants import UsageLessProvider

client = TestClient(app)
CONFIG = ProviderConfig(
    base_url="https://example.invalid/v1", api_key="test-key", model="fake-base"
)


@pytest.fixture
def run_one(monkeypatch):
    """跑一条真实（fake provider）运行并保存，返回 (payload, provider)。"""

    def _run(provider=None, mode="C"):
        engine_provider = provider or FakeProvider()
        monkeypatch.setattr(
            "app.main._engine", lambda: RunEngine(engine_provider, CONFIG)
        )
        response = client.post(
            "/api/runs", json={"scenario": "tianjin-freight", "mode": mode}
        )
        assert response.status_code == 200, response.text
        return response.json(), engine_provider

    return _run


def replay_of(payload) -> dict:
    run_id = payload["front"]["run_id"]
    response = client.get(f"/api/runs/{run_id}/replay")
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------------------------------
# 1 同一次运行：Demo 1 / Demo 2 / 重放都绑在同一条 run_id 上
# --------------------------------------------------------------------------


def test_replay_is_addressed_by_the_same_run_id(run_one):
    payload, _ = run_one()
    data = replay_of(payload)

    assert data["run_id"] == payload["front"]["run_id"] == payload["back"]["run_id"]
    # 数据来源写在载荷里：这是一条已存记录，不是一次新调用。
    assert data["source"] == "run_record"
    assert data["request_text"] == payload["front"]["request_text"]


def test_frames_follow_the_records_own_step_order(run_one):
    payload, _ = run_one()
    data = replay_of(payload)
    steps = payload["back"]["steps"]

    assert [frame["step"] for frame in data["frames"]] == [step["step"] for step in steps]
    assert [frame["phase"] for frame in data["frames"]] == [step["phase"] for step in steps]
    assert [frame["action"] for frame in data["frames"]] == [step["action"] for step in steps]


def test_the_business_action_labels_are_the_six_chain_steps(run_one):
    payload, _ = run_one()
    data = replay_of(payload)

    assert [frame["action_label"] for frame in data["frames"]] == [
        "正在解析客户需求",
        "正在判断缺口",
        "正在获取业务事实",
        "正在做业务判断",
        "正在校验",
        "正在形成最终结果",
    ]
    # 步骤条上的短名就是记录里的步骤名（去掉冒号后的自我说明）。
    assert [frame["short_label"] for frame in data["frames"]] == [
        "解析客户需求",
        "判断缺口",
        "获取可核验业务事实",
        "业务判断与人工确认点",
        "校验",
        "形成可交付结果与停止点",
    ]


# --------------------------------------------------------------------------
# 2 累计值 = 每一步真实 input_tokens + output_tokens
# --------------------------------------------------------------------------


def test_model_frames_cumulate_each_steps_real_input_plus_output(run_one):
    payload, _ = run_one()
    data = replay_of(payload)

    expected = 0
    for frame in data["frames"]:
        assert frame["from_tokens"] == expected
        if frame["kind"] == "model":
            assert frame["measured"] is True
            assert frame["step_tokens"] == frame["input_tokens"] + frame["output_tokens"]
            expected += frame["step_tokens"]
        else:
            assert frame["step_tokens"] == 0
        assert frame["to_tokens"] == expected

    assert expected > 0
    assert [frame["from_tokens"] for frame in data["frames"] if frame["kind"] == "model"]


def test_tool_frames_do_not_add_tokens(run_one):
    payload, _ = run_one()
    data = replay_of(payload)

    tool_frames = [frame for frame in data["frames"] if frame["kind"] == "tool"]
    assert len(tool_frames) == 1  # C 档的「获取可核验业务事实」
    for frame in tool_frames:
        assert frame["input_tokens"] is None and frame["output_tokens"] is None
        assert frame["step_tokens"] == 0
        assert frame["from_tokens"] == frame["to_tokens"]
        assert frame["delta_label"] == "本步模型 Token +0"
        assert frame["tool_calls"] == 3
        assert "查询船期" in frame["note"]


def test_the_final_cumulative_value_equals_the_records_own_total(run_one):
    payload, _ = run_one()
    back = payload["back"]
    data = replay_of(payload)

    assert data["frames"][-1]["to_tokens"] == back["usage"]["total_tokens"]
    assert data["final_tokens"] == back["usage"]["total_tokens"]
    assert data["complete"] is True
    assert data["playable"] is True
    assert data["totals"]["model_calls"] == back["usage"]["model_calls"]
    assert data["totals"]["tool_calls"] == back["usage"]["tool_calls"]
    assert data["totals"]["business_tasks"] == 1
    assert data["totals"]["run_status"] == "waiting_human"


def test_cached_tokens_are_not_added_a_second_time(run_one):
    """缓存是 input 的组成部分：再加一遍就是把同一批 Token 数两次。"""
    payload, _ = run_one(provider=FakeProvider(cached_tokens=64))
    back = payload["back"]
    data = replay_of(payload)

    assert back["usage"]["cached_tokens"] == 64 * back["usage"]["model_calls"]
    assert data["final_tokens"] == back["usage"]["total_tokens"]
    assert data["final_tokens"] != (
        back["usage"]["total_tokens"] + back["usage"]["cached_tokens"]
    )


def test_every_frame_carries_a_real_reason_for_its_delta(run_one):
    payload, _ = run_one()
    data = replay_of(payload)

    for frame in data["frames"]:
        if frame["kind"] == "model" and frame["measured"]:
            assert frame["note"] == (
                f"本次模型调用：输入 {frame['input_tokens']} + 输出 {frame['output_tokens']}"
            )
            assert frame["delta_label"] == f"本步模型 Token +{frame['step_tokens']}"
        else:
            assert frame["delta_label"].startswith("本步模型 Token +0") or "未计量" in frame["delta_label"]


# --------------------------------------------------------------------------
# 3 不完整的记录不能伪装成一次完整的课堂重放
# --------------------------------------------------------------------------


def test_an_unmeasured_run_cannot_pretend_to_be_a_complete_replay(run_one):
    payload, _ = run_one(provider=UsageLessProvider())
    data = replay_of(payload)

    assert data["complete"] is False
    assert data["playable"] is False
    assert any("usage" in warning for warning in data["warnings"])

    model_frames = [frame for frame in data["frames"] if frame["kind"] == "model"]
    assert model_frames
    for frame in model_frames:
        # 不猜也不补：未计量的模型步骤不增加累计值。
        assert frame["measured"] is False
        assert frame["step_tokens"] is None
        assert frame["from_tokens"] == frame["to_tokens"] == 0
        assert frame["delta_label"] == "该步 Token 未计量"
    assert data["final_tokens"] == 0


def test_a_truncated_run_is_not_offered_as_a_normal_classroom_replay(run_one):
    payload, _ = run_one(provider=FakeProvider(truncate_on_calls={3}))
    data = replay_of(payload)

    assert payload["back"]["freeze_ready"] is False
    assert data["playable"] is False
    assert any("截断" in warning for warning in data["warnings"])
    # 输出被截断说的是文字，不是数字：Token 累计照样等于记录自己的合计。
    assert data["final_tokens"] == payload["back"]["usage"]["total_tokens"]
    assert data["complete"] is True


def test_a_structure_only_record_has_no_token_to_replay():
    """没有 provider 时只有调用链结构，Token 字段为 null，没有数字可重放。"""
    response = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "C"})
    payload = response.json()

    assert payload["back"]["evidence_level"] == "structure_only"
    data = replay_of(payload)
    assert data["complete"] is False
    assert data["playable"] is False
    assert data["final_tokens"] == 0
    assert any("结构" in warning for warning in data["warnings"])


def test_replay_never_calls_the_provider(run_one):
    payload, provider = run_one()
    before = provider.call_count

    replay_of(payload)

    assert provider.call_count == before


def test_unknown_run_has_no_replay():
    assert client.get("/api/runs/nope/replay").status_code == 404


# --------------------------------------------------------------------------
# 4 Demo 1 的正面依旧没有 Token；重放是另一条路径
# --------------------------------------------------------------------------


def test_demo_1_front_carries_no_token_field(run_one):
    payload, _ = run_one()
    front = payload["front"]

    assert set(front).isdisjoint(FORBIDDEN_IN_FRONT)
    serialised = json.dumps(front, ensure_ascii=False)
    for forbidden in (
        "input_tokens",
        "output_tokens",
        "cached_tokens",
        "total_tokens",
        "model_calls",
        "tool_calls",
        "frames",
    ):
        assert forbidden not in serialised


def test_the_replay_view_ships_hidden_and_empty():
    """静态页面里重放区是隐藏的、大号数字是空的：Demo 1 打开时不会看到 Token。"""
    html = client.get("/").text

    tag = html.split('id="replay"')[1].split(">")[0]
    assert "hidden" in tag
    assert '<div class="big" id="replayNumber"></div>' in html
    # 重放的入口在 Demo 2 里，不在 Demo 1 的正面。
    assert 'id="replayOpenBtn"' in html

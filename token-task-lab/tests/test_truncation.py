"""截断：输出完整性是独立于 Token 计量的一条判断。

为什么需要这一组测试：

一份 usage 读得清清楚楚的记录，可能是被输出上限截断的结果 —— 数字完整，
内容只有一半。课堂如果把两者当同一件事，就会拿半截回答讲 Token 效率，
学员看到的“完整交付”其实是模型话没说完。

所以这里断言四件事：provider 把 finish_reason 读进来；截断被明确标记而不是
被当成正常结束；标记能落盘、能回放；A/B/C/D 的调用结构与 Token 计量口径
一个字都不变。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import ProviderConfig
from app.engine import RunEngine, token_evidence_for
from app.main import app
from app.models import (
    OUTPUT_EVIDENCE_LEVELS,
    StepRecord,
    output_evidence_for,
)
from app.provider import OpenAICompatibleProvider, parse_finish_reason
from app.scenarios import get_scenario
from app.store import RunStore
from tests.conftest import FakeProvider

client = TestClient(app)
SCENARIO = get_scenario("tianjin-freight")
CONFIG = ProviderConfig(
    base_url="https://example.invalid/v1", api_key="test-key", model="fake-base"
)


def run(mode: str, provider: FakeProvider):
    return RunEngine(provider, CONFIG).execute(
        scenario=SCENARIO, mode=mode, request_text=SCENARIO.request_text
    )


# --------------------------------------------------------------------------
# 1  Provider 从 response 里读 finish_reason
# --------------------------------------------------------------------------


def wire_provider(handler) -> OpenAICompatibleProvider:
    config = ProviderConfig(
        base_url="https://example.invalid/v1", api_key="k", model="m", timeout_s=5
    )
    return OpenAICompatibleProvider(config, client=httpx.Client(transport=httpx.MockTransport(handler)))


def reply(finish_reason, *, include=True):
    choice = {"message": {"role": "assistant", "content": "好的"}}
    if include:
        choice["finish_reason"] = finish_reason
    body = {"model": "m", "choices": [choice], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    return lambda request: httpx.Response(200, json=body)


@pytest.mark.parametrize(
    "sent, expected",
    [
        ("stop", "stop"),
        ("length", "length"),
        ("max_tokens", "max_tokens"),
        ("Stop", "stop"),  # 归一化，不改变判据本身
        (None, None),
        ("", None),
        (123, None),
    ],
)
def test_provider_reads_and_normalises_finish_reason(sent, expected):
    result = wire_provider(reply(sent)).complete([{"role": "user", "content": "hi"}])
    assert result.finish_reason == expected


def test_a_silent_gateway_reports_none_rather_than_claiming_a_normal_stop():
    """没有 finish_reason ≠ 正常结束：不能替 provider 把「没说」读成「说完了」。"""
    result = wire_provider(reply(None, include=False)).complete([{"role": "user", "content": "hi"}])
    assert result.finish_reason is None
    assert result.truncated is False  # 未上报不是截断，但也绝不是「已确认完整」


def test_parse_finish_reason_survives_an_unexpected_choice_shape():
    assert parse_finish_reason(None) is None
    assert parse_finish_reason({}) is None
    assert parse_finish_reason({"finish_reason": "stop"}) == "stop"


def test_provider_marks_only_the_capped_endings_as_truncated():
    stop = wire_provider(reply("stop")).complete([{"role": "user", "content": "hi"}])
    cut = wire_provider(reply("length")).complete([{"role": "user", "content": "hi"}])

    assert stop.truncated is False
    assert cut.truncated is True


# --------------------------------------------------------------------------
# 2  finish_reason=stop 不标记截断
# --------------------------------------------------------------------------


def test_a_normally_finished_run_is_not_marked_as_truncated():
    record = run("C", FakeProvider())

    assert record.output_evidence == "complete"
    assert record.truncated_steps == []
    assert all(step.finish_reason == "stop" for step in record.steps if step.model)
    assert all(step.truncated is False for step in record.steps)
    assert not any("截断" in note for note in record.notes)
    # 输出完整，所以 Token 计量完整的那份记录同时也是可冻结的。
    assert record.freeze_ready is True


# --------------------------------------------------------------------------
# 3  finish_reason=length 明确标记截断
# --------------------------------------------------------------------------


def test_a_capped_call_is_marked_on_its_step_and_on_the_run():
    # C 档调用顺序：1 parse、2 gaps、3 judge、4 verify、5 deliver（facts 是工具步）。
    record = run("C", FakeProvider(truncate_on_calls={3}))

    cut = [step for step in record.steps if step.truncated]
    assert len(cut) == 1
    assert cut[0].phase == "judge"
    assert cut[0].step == 4
    assert cut[0].finish_reason == "length"
    assert cut[0].status == "ok"  # 截断是输出问题，不改写步骤自己的业务状态

    assert record.output_evidence == "truncated"
    assert record.truncated_steps == [4]
    assert any("截断" in note for note in record.notes)
    assert "第 4 步" in " ".join(record.notes)


def test_truncation_does_not_contaminate_token_evidence():
    """截断说的是输出，不说数字：usage 该是 measured 就还是 measured。"""
    record = run("C", FakeProvider(truncate_on_calls={3}))

    assert record.token_evidence == "measured"
    assert record.classroom_ready is True          # 计量完整
    assert record.freeze_ready is False            # 但输出不完整
    assert record.usage.output_tokens is not None


def test_a_silent_gateway_leaves_output_completeness_unproven():
    record = run("C", FakeProvider(finish_reason=None))

    assert record.output_evidence == "unknown"
    assert record.truncated_steps == []
    assert record.classroom_ready is True
    assert record.freeze_ready is False
    assert any("finish_reason" in note for note in record.notes)


def test_output_evidence_distinguishes_the_four_cases():
    def step(finish_reason: str | None, model: str | None = "m"):
        return StepRecord(step=1, action="a", phase="p", model=model, finish_reason=finish_reason)

    assert output_evidence_for([]) == "not_executed"
    assert output_evidence_for([step(None, model=None)]) == "not_executed"
    assert output_evidence_for([step("stop")]) == "complete"
    assert output_evidence_for([step("length")]) == "truncated"
    assert output_evidence_for([step(None)]) == "unknown"
    # 一次截断就足够：整份输出不能算完整。
    assert output_evidence_for([step("stop"), step("length")]) == "truncated"
    # 一次沉默也足够：完整性没有证据。
    assert output_evidence_for([step("stop"), step(None)]) == "unknown"
    assert set(OUTPUT_EVIDENCE_LEVELS) == {"complete", "truncated", "unknown", "not_executed"}


def test_truncated_is_derived_from_finish_reason_so_the_two_cannot_drift():
    # 手写 truncated=True 而 finish_reason 正常：以 provider 的原因为准。
    assert StepRecord(step=1, action="a", phase="p", finish_reason="stop", truncated=True).truncated is False
    assert StepRecord(step=1, action="a", phase="p", finish_reason="length").truncated is True
    # 旧的记录没有这两个字段：不臆断为完整。
    old = StepRecord(step=1, action="a", phase="p", model="m")
    assert old.finish_reason is None and old.truncated is False


# --------------------------------------------------------------------------
# 4  截断状态可以持久化和回放
# --------------------------------------------------------------------------


def test_truncation_survives_a_save_and_load(tmp_path):
    store = RunStore(tmp_path / "runs")
    record = run("C", FakeProvider(truncate_on_calls={3}))
    path = store.save(record)

    loaded = store.get(record.run_id)
    assert loaded is not None
    assert loaded.model_dump() == record.model_dump()
    assert loaded.output_evidence == "truncated"
    assert loaded.truncated_steps == [4]
    assert loaded.steps[3].finish_reason == "length"
    assert loaded.steps[3].truncated is True
    assert loaded.freeze_ready is False

    # 落盘的 JSON 用 cat 就能看出哪一步被截断。
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["steps"][3]["finish_reason"] == "length"
    assert on_disk["steps"][3]["truncated"] is True
    assert on_disk["output_evidence"] == "truncated"


def test_a_record_saved_before_finish_reason_existed_is_not_read_back_as_complete():
    """旧的 runs/*.json 没有这两个字段：回放时必须诚实地说「未上报」。"""
    from app.models import RunRecord

    payload = run("C", FakeProvider()).model_dump()
    for step in payload["steps"]:
        step.pop("finish_reason", None)
        step.pop("truncated", None)
    payload.pop("output_evidence", None)
    payload.pop("truncated_steps", None)

    loaded = RunRecord(**payload)
    assert loaded.output_evidence == "unknown"
    assert loaded.freeze_ready is False
    # Token 口径不受影响：旧记录该是 measured 还是 measured。
    assert loaded.token_evidence == "measured"


def test_a_truncated_run_replays_through_the_api_with_its_marker_intact(monkeypatch):
    monkeypatch.setattr(
        "app.main._engine", lambda: RunEngine(FakeProvider(truncate_on_calls={3}), CONFIG)
    )
    payload = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "C"}).json()
    run_id = payload["front"]["run_id"]

    replayed = client.get(f"/api/runs/{run_id}").json()
    back = replayed["back"]

    assert back["output_evidence"] == "truncated"
    assert back["truncated_steps"] == [4]
    assert back["freeze_ready"] is False
    assert back["classroom_ready"] is True
    assert any(step["truncated"] for step in back["steps"])
    # 步骤表要能指出是哪一步、以及 provider 报的原始原因。
    cut = next(step for step in back["steps"] if step["truncated"])
    assert cut["finish_reason"] == "length"
    assert replayed["back"] == payload["back"]


# --------------------------------------------------------------------------
# 5  Demo 1 正面仍然看不到截断标记
# --------------------------------------------------------------------------


def test_demo_1_front_carries_no_truncation_fields_even_when_truncated(monkeypatch):
    from app.views import FORBIDDEN_IN_FRONT

    monkeypatch.setattr(
        "app.main._engine", lambda: RunEngine(FakeProvider(truncate_on_calls={3}), CONFIG)
    )
    payload = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "C"}).json()

    assert set(payload["front"]).isdisjoint(FORBIDDEN_IN_FRONT)
    serialised = json.dumps(payload["front"], ensure_ascii=False)
    for forbidden in ("finish_reason", "truncated", "output_evidence", "freeze_ready"):
        assert forbidden not in serialised
    # 同一份记录，翻到背面就能看见。
    assert payload["back"]["output_evidence"] == "truncated"


def test_the_page_keeps_truncation_markup_out_of_the_business_front():
    page = client.get("/").text
    back_start = page.index('id="back"')
    front_section = page[page.index('id="front"'):back_start]
    run_side = page[back_start:]

    assert "输出被截断" not in front_section
    assert "finish_reason" not in front_section
    # 背面与实验对照必须明说。
    assert "输出被截断" in run_side
    assert "finish_reason" in run_side
    assert "输出完整性" in run_side
    assert "OUTPUT_EVIDENCE_TEXT" in run_side


# --------------------------------------------------------------------------
# 6  A/B/C/D 实验对照能看出某档存在截断
# --------------------------------------------------------------------------


def experiment_provider(truncate_on_calls=frozenset()) -> FakeProvider:
    return FakeProvider(truncate_on_calls=truncate_on_calls)


def test_the_comparison_table_shows_which_mode_was_truncated(monkeypatch):
    # 调用顺序 A(1) B(2) C(3-7) D(8-14)：截断第 5 次调用 = C 档的 judge 步。
    monkeypatch.setattr(
        "app.main._engine", lambda: RunEngine(experiment_provider({5}), CONFIG)
    )
    experiment_id = client.post(
        "/api/experiments", json={"scenario": "tianjin-freight", "modes": ["A", "B", "C", "D"]}
    ).json()["experiment_id"]

    listing = next(
        item
        for item in client.get("/api/experiments").json()["experiments"]
        if item["experiment_id"] == experiment_id
    )
    rows = {row["mode"]: row for row in listing["records"]}

    assert rows["C"]["output_evidence"] == "truncated"
    assert rows["C"]["truncated_calls"] == 1
    # 计量完整 ≠ 输出完整：C 档仍然“可用于 Token 实验”，但不可冻结。
    assert rows["C"]["classroom_ready"] is True
    assert rows["C"]["freeze_ready"] is False

    for mode in ("A", "B", "D"):
        assert rows[mode]["output_evidence"] == "complete"
        assert rows[mode]["freeze_ready"] is True
        assert rows[mode]["truncated_calls"] == 0


def test_health_separates_token_evidence_from_output_completeness(monkeypatch):
    monkeypatch.setattr(
        "app.main._engine", lambda: RunEngine(FakeProvider(truncate_on_calls={1}), CONFIG)
    )
    client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "A"})

    health = client.get("/api/health").json()
    assert health["classroom_ready_runs"] == 1   # Token 计量完整
    assert health["freeze_ready_runs"] == 0      # 输出不完整
    assert health["truncated_live_runs"] == 1
    assert any("截断" in note for note in health["notes"])


def test_health_counts_a_complete_run_as_freeze_ready(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "A"})

    health = client.get("/api/health").json()
    assert health["classroom_ready_runs"] == 1
    assert health["freeze_ready_runs"] == 1
    assert health["truncated_live_runs"] == 0


# --------------------------------------------------------------------------
# 7  调用结构、计量口径与既有行为一个字都不变
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode, model_calls, tool_calls",
    [("A", 1, 0), ("B", 1, len(SCENARIO.tools)), ("C", 5, 3), ("D", 7, 6)],
)
def test_call_structure_is_unchanged(mode, model_calls, tool_calls):
    """C 仍是 5 次模型 + 3 次工具；D 仍是真实重复（7 次模型 + 6 次工具）。"""
    record = run(mode, FakeProvider())

    assert record.usage.model_calls == model_calls
    assert record.usage.tool_calls == tool_calls


def test_finish_reason_reporting_does_not_change_any_token_number():
    reporting = run("C", FakeProvider())
    silent = run("C", FakeProvider(finish_reason=None))

    # 同一个 provider 的两种上报方式，数字必须一模一样：截断标记不是数字来源。
    assert reporting.usage.model_dump() == silent.usage.model_dump()
    assert [s.input_tokens for s in reporting.steps] == [s.input_tokens for s in silent.steps]
    assert token_evidence_for(reporting.steps) == token_evidence_for(silent.steps) == "measured"


def test_truncation_does_not_touch_the_fact_state_logic():
    """天津船期的 missing / unverified / verified 判断与截断无关。"""
    record = run("C", FakeProvider(truncate_on_calls={3}))
    facts = next(step for step in record.steps if step.phase == "facts")

    assert facts.status == "blocked"
    assert {fact.name: fact.state for fact in facts.facts} == {
        "sailing_schedule": "unverified",
        "rate_card": "missing",
        "space_check": "missing",
    }
    assert record.run_status == "waiting_human"


def test_the_experiment_id_still_ties_the_four_modes_together(monkeypatch):
    monkeypatch.setattr(
        "app.main._engine", lambda: RunEngine(FakeProvider(truncate_on_calls={5}), CONFIG)
    )
    body = client.post(
        "/api/experiments", json={"scenario": "tianjin-freight", "modes": ["A", "B", "C", "D"]}
    ).json()

    assert body["experiment_id"]
    assert [item["front"]["mode"] for item in body["records"]] == ["A", "B", "C", "D"]
    assert {item["back"]["experiment_id"] for item in body["records"]} == {body["experiment_id"]}


# --------------------------------------------------------------------------
# 8  输出长度约束写在提示词里，不靠调大 max_tokens
# --------------------------------------------------------------------------


def test_max_tokens_is_still_the_classroom_default():
    """不允许用「把上限调大」来掩盖输出过长，所以这个值必须没被改过。"""
    assert ProviderConfig().max_tokens == 900


def test_every_chain_step_carries_an_output_budget():
    provider = FakeProvider()
    run("C", provider)
    prompts = [request["messages"][-1]["content"] for request in provider.requests]

    # C 档顺序：parse / gaps / judge / verify / deliver。
    for prompt, limit in zip(prompts, (150, 150, 250, 250, 400)):
        assert f"总字数不超过 {limit} 字" in prompt
        assert "不复述输入" in prompt


def test_the_shared_system_prompt_asks_for_concise_output():
    provider = FakeProvider()
    run("C", provider)
    systems = [request["messages"][0]["content"] for request in provider.requests]

    assert all("只给结论" in system for system in systems)


def test_mode_a_and_b_ask_for_a_sendable_answer_within_the_delivery_budget():
    provider = FakeProvider()
    run("A", provider)
    run("B", provider)

    a_messages = provider.requests[0]["messages"]
    b_messages = provider.requests[1]["messages"]

    assert "总字数不超过 400 字" in a_messages[0]["content"]
    assert "可直接发送给客户" in a_messages[0]["content"]
    assert "总字数不超过 400 字" in b_messages[-1]["content"]
    # A 档交给模型的客户原话本身没有被动过。
    assert a_messages[-1]["content"] == SCENARIO.request_text


def test_mode_d_repeated_steps_carry_the_same_budget_as_their_c_mode_counterparts():
    provider = FakeProvider()
    run("D", provider)
    prompts = [request["messages"][-1]["content"] for request in provider.requests]

    # D 档调用顺序：parse ×2、judge ×2、verify ×2、deliver。
    for prompt, limit in zip(prompts, (250, 250, 250, 250, 250, 250, 400)):
        assert f"总字数不超过 {limit} 字" in prompt


# --------------------------------------------------------------------------
# 9  课前录制脚本把截断说出来（重跑真实实验时看的就是它的输出）
# --------------------------------------------------------------------------


def load_record_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "record_runs.py"
    spec = importlib.util.spec_from_file_location("record_runs_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_record_script(monkeypatch, tmp_path, provider, modes, capsys):
    module = load_record_script()
    monkeypatch.setattr(module, "load_provider_config", lambda: CONFIG)
    monkeypatch.setattr(module, "OpenAICompatibleProvider", lambda config: provider)
    monkeypatch.setattr(module, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr("sys.argv", ["record_runs.py", *modes])

    code = module.main()
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_recorder_reports_and_refuses_to_freeze_a_truncated_batch(monkeypatch, tmp_path, capsys):
    # A 是第 1 次调用，C 档是 2–6：截断第 2 次 = C 档第 1 步（解析）。
    code, out, err = run_record_script(
        monkeypatch, tmp_path, FakeProvider(truncate_on_calls={2}), ["A", "C"], capsys
    )

    assert code == 1  # 有截断 = 这组数据不能冻结，脚本以非零码退出
    assert "课堂可用于 Token 实验的记录：2/2 档" in out
    assert "适合课堂冻结的档位：1/2 档" in out
    # 逐档标出被截断的步号，并在收尾表格里给出截断次数。
    assert "第 1 步被长度上限截断" in out
    assert "[输出被截断 1 次]" in out
    assert "输出被长度上限截断（C）" in err
    assert f"{'截断':>6}" in out  # 对比表最后一列是截断次数

    # 落盘的记录带着标记，课堂回放时看得见。
    saved = RunStore(tmp_path / "runs").list_summaries()
    by_mode = {row.mode: row for row in saved}
    assert by_mode["C"].output_evidence == "truncated"
    assert by_mode["C"].truncated_calls == 1
    assert by_mode["C"].freeze_ready is False
    assert by_mode["A"].freeze_ready is True


def test_the_recorder_confirms_a_clean_batch(monkeypatch, tmp_path, capsys):
    code, out, err = run_record_script(
        monkeypatch, tmp_path, FakeProvider(), ["A", "C"], capsys
    )

    assert code == 0
    assert "课堂可用于 Token 实验的记录：2/2 档" in out
    assert "适合课堂冻结的档位：2/2 档" in out
    assert "截断" not in err
    assert all(row.freeze_ready for row in RunStore(tmp_path / "runs").list_summaries())

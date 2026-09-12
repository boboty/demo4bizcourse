"""The three claims the class depends on, and the experiment grouping.

Each test here exists because a plausible implementation could satisfy the
architecture and still make the lecture false:

1. Demo 1 must show what this run produced, not what the scenario file says.
2. "The tool returned something" must not be read as "we have a usable fact".
3. "A real model call happened" must not be read as "we have token evidence".
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import ProviderConfig
from app.engine import RunEngine, token_evidence_for
from app.main import app
from app.models import StepRecord
from app.provider import ProviderResult
from app.scenarios import get_scenario
from app.scenarios.base import Material, Scenario, ToolSpec
from app.tools import ToolBox
from tests.conftest import FakeProvider

client = TestClient(app)
SCENARIO = get_scenario("tianjin-freight")
CONFIG = ProviderConfig(
    base_url="https://example.invalid/v1", api_key="test-key", model="fake-base"
)


def post_experiment(modes=("A", "B", "C", "D"), request_text=""):
    response = client.post(
        "/api/experiments",
        json={"scenario": "tianjin-freight", "modes": list(modes), "request_text": request_text},
    )
    assert response.status_code == 200, response.text
    return response.json()


def observations_by_role(front: dict) -> dict[str, dict]:
    return {item["role"]: item for item in front["observations"]}


# --------------------------------------------------------------------------
# P0-1  Demo 1 shows this run's output, not the constructor's answer
# --------------------------------------------------------------------------


def test_demo_1_observations_come_from_the_models_own_output(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    front = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "C"}).json()["front"]

    seen = observations_by_role(front)
    # C 档调用顺序：parse=1, gaps=2, judge=3, verify=4, deliver=5。
    assert seen["understanding"]["text"] == "回答1"
    assert seen["gaps"]["text"] == "回答2"
    assert seen["judgment"]["text"] == "回答3"
    assert seen["verification"]["text"] == "回答4"
    assert seen["delivery"]["text"] == "回答5"
    assert all(item["executed"] for item in front["observations"])


def test_demo_1_baseline_is_labelled_as_preset_and_kept_out_of_the_main_area(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    front = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "C"}).json()["front"]

    # The preset answers are no longer top-level front fields...
    assert "known" not in front and "missing" not in front and "human_gates" not in front
    # ...they live in a labelled baseline block.
    baseline = front["baseline"]
    assert baseline["label"] == "场景验收基准"
    assert "不是本次运行产生的" in baseline["note"]
    assert baseline["known"] and baseline["missing"]
    assert baseline["matches_request"] is True

    # The main area is the run's own output: every observation is a chain step,
    # none of them is the label the preset block uses.
    assert all(item["label"] != baseline["label"] for item in front["observations"])


def test_swapping_the_input_invalidates_the_preset_baseline(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    front = client.post(
        "/api/runs",
        json={
            "scenario": "tianjin-freight",
            "mode": "C",
            "request_text": "青岛到仁川，一个40HQ，下周五货好。",
        },
    ).json()["front"]

    assert front["request_text"] == "青岛到仁川，一个40HQ，下周五货好。"
    assert front["baseline"]["matches_request"] is False
    assert "已不适用" in front["baseline"]["mismatch_note"]
    # The observations still describe this run, not the 天津 baseline.
    assert observations_by_role(front)["understanding"]["text"] == "回答1"


def test_a_structure_only_run_has_no_observations_but_keeps_the_baseline():
    front = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "C"}).json()["front"]

    assert front["evidence_level"] == "structure_only"
    assert all(item["executed"] is False for item in front["observations"])
    assert all(item["text"] is None for item in front["observations"])
    assert front["baseline"]["known"]


def test_mode_a_has_no_task_breakdown_to_show(monkeypatch):
    """A 档没有拆解步骤，正面就不该凭空多出「AI 实际识别缺口」。"""
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    front = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "A"}).json()["front"]

    roles = {item["role"] for item in front["observations"]}
    assert roles == {"result"}
    assert observations_by_role(front)["result"]["text"] == "回答1"


def test_demo_1_still_leaks_no_token_field(monkeypatch):
    import json

    from app.views import FORBIDDEN_IN_FRONT

    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    front = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "D"}).json()["front"]

    assert set(front).isdisjoint(FORBIDDEN_IN_FRONT)
    serialised = json.dumps(front, ensure_ascii=False)
    for forbidden in ("input_tokens", "output_tokens", "cached_tokens", "total_tokens", "latency_ms"):
        assert forbidden not in serialised


# --------------------------------------------------------------------------
# P0-2  available ≠ verified
# --------------------------------------------------------------------------


def test_the_schedule_fixture_is_unverified_not_usable():
    spec = SCENARIO.tool("sailing_schedule")
    assert spec.available is True
    assert spec.verified is False
    assert spec.fact_state == "unverified"
    assert spec.usable_as_fact is False


def test_an_unverified_result_blocks_a_verifiable_fact_step(provider_config):
    record = RunEngine(FakeProvider(), provider_config).execute(
        scenario=SCENARIO, mode="C", request_text=SCENARIO.request_text
    )
    facts = next(step for step in record.steps if step.phase == "facts")

    # 船期有结果，但它是教学构造数据 —— 这一步仍然不能算完成。
    assert facts.status == "blocked"
    assert "查询船期" in facts.detail
    assert "查询运价" in facts.detail

    states = {fact.name: fact.state for fact in facts.facts}
    assert states == {
        "sailing_schedule": "unverified",
        "rate_card": "missing",
        "space_check": "missing",
    }
    labels = {fact.name: fact.state_label for fact in facts.facts}
    assert labels["sailing_schedule"] == "有结果但未核验"
    assert labels["rate_card"] == "无结果"


def test_the_record_exposes_three_states_not_a_boolean():
    facts = ToolBox(scenario=SCENARIO)
    facts.call_many(["sailing_schedule", "rate_card"])
    states = [call.fact_state for call in facts.calls]
    assert states == ["unverified", "missing"]
    assert len(facts.unusable_facts()) == 2


def test_a_fully_verified_scenario_does_not_block_the_fact_step(provider_config):
    """The controller: when every tool is verifiable, the step completes."""
    verified_scenario = Scenario(
        key="verified-demo",
        name="全部可核验示例",
        request_text="测试",
        task="测试",
        known=("a",),
        missing=("b",),
        human_gates=("c",),
        materials=(Material(key="m", title="资料", body="内容", verified=True),),
        tools=(
            ToolSpec(
                name="ok_tool",
                title="可核验查询",
                description="返回已核验结果",
                payload={"value": 1},
                available=True,
                verified=True,
            ),
            ToolSpec(
                name="dead_tool",
                title="可核验查询二",
                description="返回已核验结果",
                payload={"value": 2},
                available=True,
                verified=True,
            ),
        ),
        fact_tools=("ok_tool", "dead_tool"),
    )
    record = RunEngine(FakeProvider(), provider_config).execute(
        scenario=verified_scenario, mode="C", request_text="测试"
    )
    facts = next(step for step in record.steps if step.phase == "facts")

    assert facts.status == "ok"
    assert "均已核验" in facts.detail
    assert all(fact.state == "verified" for fact in facts.facts)


# --------------------------------------------------------------------------
# P0-3  execution evidence ≠ token evidence
# --------------------------------------------------------------------------


class UsageLessProvider(FakeProvider):
    """A gateway that returns content but no usage block at all."""

    def complete(self, messages, *, model=None, temperature=None, max_tokens=None):
        result = super().complete(messages, model=model)
        return ProviderResult(
            text=result.text,
            model=result.model,
            input_tokens=None,
            output_tokens=None,
            cached_tokens=None,
            latency_ms=result.latency_ms,
            usage_raw={},
        )


def test_a_real_run_without_usage_is_not_classroom_ready(provider_config):
    record = RunEngine(UsageLessProvider(), provider_config).execute(
        scenario=SCENARIO, mode="A", request_text=SCENARIO.request_text
    )

    # It really ran...
    assert record.evidence_level == "live"
    assert record.usage.model_calls == 1
    assert record.steps[0].model == "fake-base"
    # ...but there is no token evidence.
    assert record.token_evidence == "not_reported"
    assert record.usage.input_tokens is None
    assert record.classroom_ready is False
    assert any("不能作为 Token 实验记录" in note for note in record.notes)


def test_a_measured_run_is_classroom_ready(provider_config):
    record = RunEngine(FakeProvider(), provider_config).execute(
        scenario=SCENARIO, mode="A", request_text=SCENARIO.request_text
    )
    assert record.token_evidence == "measured"
    assert record.classroom_ready is True


def test_token_evidence_distinguishes_the_four_cases():
    def step(model, in_t, out_t):
        return StepRecord(
            step=1, action="a", phase="p", model=model, input_tokens=in_t, output_tokens=out_t
        )

    assert token_evidence_for([]) == "not_executed"
    assert token_evidence_for([step(None, None, None)]) == "not_executed"
    assert token_evidence_for([step("m", None, None)]) == "not_reported"
    assert token_evidence_for([step("m", 10, 5), step("m", None, None)]) == "partial"
    assert token_evidence_for([step("m", 10, 5), step("m", 4, 2)]) == "measured"
    # Output tokens alone are not enough to call usage measured.
    assert token_evidence_for([step("m", 10, None)]) == "not_reported"


def test_health_separates_real_runs_from_classroom_ready_ones(monkeypatch):
    monkeypatch.setattr(
        "app.main._engine", lambda: RunEngine(UsageLessProvider(), CONFIG)
    )
    client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "A"})

    health = client.get("/api/health").json()
    assert health["saved_live_runs"] == 1
    assert health["classroom_ready_runs"] == 0
    assert health["unmeasured_live_runs"] == 1
    assert any("不能作为 Token 实验记录" in note for note in health["notes"])


def test_health_counts_a_measured_run_as_classroom_ready(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "A"})

    health = client.get("/api/health").json()
    assert health["saved_live_runs"] == 1
    assert health["classroom_ready_runs"] == 1
    assert health["unmeasured_live_runs"] == 0


# --------------------------------------------------------------------------
# P1  A/B/C/D as one experiment
# --------------------------------------------------------------------------


def test_an_experiment_runs_all_four_modes_under_one_id(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    body = post_experiment()

    assert body["experiment_id"]
    assert [item["front"]["mode"] for item in body["records"]] == ["A", "B", "C", "D"]
    for item in body["records"]:
        assert item["back"]["experiment_id"] == body["experiment_id"]

    ids = {item["front"]["run_id"] for item in body["records"]}
    assert len(ids) == 4


def test_the_comparison_table_has_real_per_mode_numbers(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    experiment_id = post_experiment()["experiment_id"]

    listing = next(
        item
        for item in client.get("/api/experiments").json()["experiments"]
        if item["experiment_id"] == experiment_id
    )
    rows = {row["mode"]: row for row in listing["records"]}

    assert set(rows) == {"A", "B", "C", "D"}
    assert rows["A"]["model_calls"] == 1 and rows["A"]["tool_calls"] == 0
    assert rows["D"]["model_calls"] > rows["C"]["model_calls"]
    assert rows["D"]["input_tokens"] > rows["C"]["input_tokens"]
    assert all(row["classroom_ready"] for row in rows.values())


def test_every_record_in_an_experiment_shares_one_request_text(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    body = post_experiment(request_text="青岛到仁川，一个40HQ。")

    texts = {item["front"]["request_text"] for item in body["records"]}
    assert texts == {"青岛到仁川，一个40HQ。"}


def test_an_experiment_can_be_fetched_whole(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    experiment_id = post_experiment(modes=("A", "C"))["experiment_id"]

    body = client.get(f"/api/experiments/{experiment_id}").json()
    assert body["experiment_id"] == experiment_id
    assert [item["front"]["mode"] for item in body["records"]] == ["A", "C"]
    assert all(item["back"]["steps"] for item in body["records"])


def test_single_runs_are_not_dressed_up_as_an_experiment(monkeypatch):
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(FakeProvider(), CONFIG))
    client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "C"})

    listing = client.get("/api/experiments").json()["experiments"]
    singles = [item for item in listing if item["experiment_id"] is None]
    assert singles
    assert "不属于任何对照实验" in singles[0]["label"]
    assert all(row["experiment_id"] is None for row in singles[0]["records"])


def test_unknown_experiment_is_404():
    assert client.get("/api/experiments/nope").status_code == 404


def test_unknown_mode_in_an_experiment_is_rejected():
    response = client.post(
        "/api/experiments", json={"scenario": "tianjin-freight", "modes": ["A", "Z"]}
    )
    assert response.status_code == 400


def test_an_experiment_with_no_modes_is_rejected():
    response = client.post(
        "/api/experiments", json={"scenario": "tianjin-freight", "modes": []}
    )
    assert response.status_code == 400

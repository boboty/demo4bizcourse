"""API contract: Demo 1 never sees a token number, Demo 2 replays from run_id."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import ProviderConfig
from app.engine import RunEngine
from app.main import app
from app.store import RunStore
from app.views import FORBIDDEN_IN_FRONT
from tests.conftest import FakeProvider

client = TestClient(app)


def post_run(mode: str, **overrides):
    body = {"scenario": "tianjin-freight", "mode": mode, "request_text": ""}
    body.update(overrides)
    response = client.post("/api/runs", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def use_fake_provider(monkeypatch, **kwargs):
    config = ProviderConfig(
        base_url="https://example.invalid/v1", api_key="test-key", model="fake-base"
    )
    provider = FakeProvider(**kwargs)
    monkeypatch.setattr("app.main._engine", lambda: RunEngine(provider, config))
    return provider


# ---------------------------------------------------------------- startup


def test_scenario_contract():
    body = client.get("/api/scenarios").json()
    assert "tianjin-freight" in body
    scenario = body["tianjin-freight"]
    assert scenario["human_gates"]
    assert scenario["missing"]
    assert scenario["next_actions"]
    assert any(tool["available"] is False for tool in scenario["tools"])


def test_app_starts_and_reports_missing_provider():
    health = client.get("/api/health").json()
    assert health["provider_ready"] is False
    assert set(health["provider"]["missing_settings"]) == {
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
    }
    assert "api_key" not in health["provider"]


def test_index_page_serves():
    response = client.get("/")
    assert response.status_code == 200
    assert "Token Task Lab" in response.text


def test_index_page_keeps_the_token_columns_inside_the_back_section():
    """Every token column header lives in the section that starts hidden."""
    page = client.get("/").text
    back_start = page.index('id="back"')
    back_section = page[back_start:]
    front_section = page[page.index('id="front"'):back_start]

    for header in ("输入", "输出", "缓存", "耗时"):
        assert header in back_section
        assert header not in front_section

    # And the back section is the one that starts collapsed.
    assert 'id="back" class="card back"' in page
    assert ".back{display:none}" in page


# ---------------------------------------------------------------- structure only


def test_run_without_provider_is_structure_only_and_fabricates_nothing():
    payload = post_run("C")
    back = payload["back"]

    assert back["evidence_level"] == "structure_only"
    assert back["run_status"] == "not_executed"
    assert back["usage"]["input_tokens"] is None
    assert back["usage"]["output_tokens"] is None
    assert back["usage"]["cached_tokens"] is None
    assert back["usage"]["model_calls"] == 0
    assert all(step["status"] == "not_executed" for step in back["steps"])
    assert back["run_id"]


def test_invalid_mode_is_rejected():
    response = client.post("/api/runs", json={"scenario": "tianjin-freight", "mode": "X"})
    assert response.status_code == 400


def test_unknown_scenario_is_rejected():
    response = client.post("/api/runs", json={"scenario": "nope", "mode": "C"})
    assert response.status_code == 404


# ---------------------------------------------------------------- front/back split


def test_demo_1_payload_carries_no_token_or_step_fields(monkeypatch):
    use_fake_provider(monkeypatch)
    payload = post_run("C")

    front = payload["front"]
    assert set(front).isdisjoint(FORBIDDEN_IN_FRONT)
    serialised = json.dumps(front, ensure_ascii=False)
    for forbidden in ("input_tokens", "output_tokens", "cached_tokens", "usage", "latency_ms"):
        assert forbidden not in serialised
    # But Demo 1 does get the business structure it is supposed to show.
    assert front["known"] and front["missing"] and front["human_gates"]
    assert front["next_actions"] and front["dependencies"]


def test_demo_2_payload_carries_the_numbers(monkeypatch):
    use_fake_provider(monkeypatch)
    back = post_run("C")["back"]

    assert back["evidence_level"] == "live"
    assert back["usage"]["model_calls"] == 5
    assert back["usage"]["input_tokens"] > 0
    assert back["claim_audit"]["verdict"]


# ---------------------------------------------------------------- persistence + replay


def test_a_live_run_is_saved_and_replays_identically(monkeypatch, isolated_env):
    use_fake_provider(monkeypatch)
    payload = post_run("C")
    run_id = payload["front"]["run_id"]

    assert payload["saved_path"]
    assert RunStore(isolated_env / "runs").get(run_id) is not None

    replayed = client.get(f"/api/runs/{run_id}").json()
    assert replayed["front"] == payload["front"]
    assert replayed["back"] == payload["back"]


def test_recorded_runs_are_listed_with_their_totals(monkeypatch):
    use_fake_provider(monkeypatch)
    first = post_run("A")["front"]["run_id"]
    second = post_run("B")["front"]["run_id"]

    records = client.get("/api/runs").json()["records"]
    ids = [row["run_id"] for row in records]
    assert first in ids and second in ids

    row = next(r for r in records if r["run_id"] == second)
    assert row["mode"] == "B"
    assert row["model_calls"] == 1
    assert row["tool_calls"] == 3
    assert row["input_tokens"] > 0


def test_replaying_an_unknown_run_is_404():
    assert client.get("/api/runs/does-not-exist").status_code == 404


def test_save_can_be_switched_off(monkeypatch):
    use_fake_provider(monkeypatch)
    payload = post_run("A", save=False)
    assert payload["saved_path"] is None
    before = client.get("/api/runs").json()["records"]

    run_id = payload["front"]["run_id"]
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert all(row["run_id"] != run_id for row in before)


def test_run_id_in_the_url_cannot_escape_the_runs_directory(isolated_env):
    assert client.get("/api/runs/..%2F..%2Fetc%2Fpasswd").status_code == 404
    assert client.get("/api/runs/....//etc").status_code == 404


# ---------------------------------------------------------------- request text


def test_blank_request_text_falls_back_to_the_scenario_original():
    payload = post_run("A", request_text="   ")
    assert payload["front"]["request_text"] == "天津新港到釜山，下周三货好，两个20GP，帮我看看船期和价格。"


def test_custom_request_text_is_kept_verbatim(monkeypatch):
    use_fake_provider(monkeypatch)
    payload = post_run("A", request_text="换一批：青岛到仁川，一个40HQ。")
    assert payload["front"]["request_text"] == "换一批：青岛到仁川，一个40HQ。"


@pytest.mark.parametrize("mode", ["A", "B", "C", "D"])
def test_every_mode_is_reachable_without_a_provider(mode):
    payload = post_run(mode)
    assert payload["front"]["mode"] == mode
    assert payload["back"]["steps"]

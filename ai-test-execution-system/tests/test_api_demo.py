import json
from pathlib import Path
from types import SimpleNamespace

from instructor.run_api_demo import run_normal, run_timeout
from scripts.run_pay_order_ios import read_case


ROOT = Path(__file__).resolve().parents[1]


def test_api_demo_normal_composes_existing_skills_and_cleans_up(monkeypatch, tmp_path: Path) -> None:
    import instructor.run_api_demo as module

    case = read_case(ROOT / "cases" / "pay_order.yaml")
    calls = []

    monkeypatch.setattr(module, "require_success", lambda url, **kwargs: calls.append((url, kwargs)) or {})
    monkeypatch.setattr(
        module,
        "prepare_pending_order",
        lambda context: setattr(context, "order_id", "order-001") or {"order_id": "order-001"},
    )
    monkeypatch.setattr(
        module,
        "http_request",
        lambda *args, **kwargs: SimpleNamespace(status_code=200, ok=True),
    )
    monkeypatch.setattr(
        module,
        "assert_business_state",
        lambda context: {"facts": {"order_status": "PAID"}},
    )
    monkeypatch.setattr(module, "reset_test_state", lambda context: {"cleanup": "PASS"})

    artifact_dir = tmp_path / "normal"
    result = run_normal(case, "http://demo", artifact_dir)

    assert result["result"] == "PASS"
    assert result["cleanup"] == "PASS"
    assert any(call[0].endswith("/api/config") for call in calls)
    assert json.loads((artifact_dir / "result.json").read_text()) == result


def test_api_demo_timeout_modes_delegate_to_business_retry_policy(monkeypatch, tmp_path: Path) -> None:
    import instructor.run_api_demo as module

    case = read_case(ROOT / "cases" / "pay_order.yaml")
    captured = {}

    def fake_retry(case_arg, base_url, configuration, artifact_dir, observer_context=None):
        captured["configuration"] = configuration
        captured["observer_context"] = observer_context
        artifact_dir.mkdir(parents=True, exist_ok=True)
        history = {
            "decision": "RETRY_ALLOWED",
            "attempts": [{"http_status": 504, "business_facts": {"payment_count": 0}}],
        }
        (artifact_dir / "retry_history.json").write_text(json.dumps(history))
        return {"result": "PASS"}

    monkeypatch.setattr(module, "run_business_retry", fake_retry)
    result = run_timeout("timeout-before", case, "http://demo", tmp_path / "before")

    assert result["result"] == "PASS"
    assert captured["configuration"]["payment_mode"] == "timeout_before_commit"
    assert captured["observer_context"] == {
        "demo": "demo2",
        "run_id": (tmp_path / "before").parent.name,
        "scenario_id": "timeout-before",
    }

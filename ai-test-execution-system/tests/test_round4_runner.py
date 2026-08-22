import json
from pathlib import Path

from runner.report import build_report
from runner.retry_policy import run_business_retry
from runner.run_plan import load_plan
from runner.suite_runner import load_suite
from scripts.run_pay_order_ios import read_case
from skills.assert_business_state import assert_business_state
from skills.contracts import ExecutionContext, SkillError
from tools.api import HttpResponse


ROOT = Path(__file__).resolve().parents[1]


def test_round4_suite_and_run_plan_are_serial_and_cover_required_scenarios() -> None:
    suite = load_suite(ROOT / "suites" / "nightly.yaml")
    plan = load_plan(ROOT / "schedules" / "nightly.yaml")
    assert suite["execution_mode"] == "serial"
    assert plan["execution_mode"] == "serial"
    assert {item["scenario_id"] for item in suite["scenarios"]} == {
        "normal_payment",
        "normal_payment_repeat",
        "product_bug_inventory_not_decremented",
        "timeout_before_commit_business_retry",
        "timeout_after_commit_no_retry",
    }
    assert all(item["task"] == "cases/pay_order.yaml" for item in suite["scenarios"])


def _fake_case():
    return read_case(ROOT / "cases" / "pay_order.yaml")


def test_timeout_before_commit_allows_exactly_one_retry_after_facts(monkeypatch, tmp_path: Path) -> None:
    import runner.retry_policy as module

    case = _fake_case()
    calls = []
    facts = [
        {
            "order_status": "PENDING_PAY",
            "payment_count": 0,
            "payment_record": None,
            "inventory": {"available_quantity": 10},
        },
        {
            "order_status": "PAID",
            "payment_count": 1,
            "payment_record": {"status": "SUCCEEDED"},
            "inventory": {"available_quantity": 9},
        },
    ]

    def fake_require_success(url, method="GET", payload=None, timeout=90):
        if "/facts" in url:
            return facts.pop(0)
        return {"ok": True}

    def fake_prepare(context):
        context.order_id = "order-001"
        return {"order_id": context.order_id}

    monkeypatch.setattr(module, "require_success", fake_require_success)
    monkeypatch.setattr(module, "prepare_pending_order", fake_prepare)
    monkeypatch.setattr(module, "reset_test_state", lambda context: None)
    monkeypatch.setattr(
        module,
        "http_request",
        lambda *args, **kwargs: (calls.append(kwargs) or HttpResponse(504, {}))
        if len(calls) == 0
        else (calls.append(kwargs) or HttpResponse(200, {})),
    )

    result = run_business_retry(
        case,
        "http://demo",
        {"ui_version": "v1", "payment_mode": "timeout_before_commit", "product_bug_mode": "off"},
        tmp_path / "before",
    )
    history = json.loads((tmp_path / "before" / "retry_history.json").read_text(encoding="utf-8"))
    assert result["result"] == "PASS"
    assert history["decision"] == "RETRY_ALLOWED"
    assert [attempt["http_status"] for attempt in history["attempts"]] == [504, 200]
    assert result["retry_count"] == 1


def test_timeout_after_commit_forbids_retry_and_keeps_one_payment(monkeypatch, tmp_path: Path) -> None:
    import runner.retry_policy as module

    case = _fake_case()
    calls = []
    committed = {
        "order_status": "PAID",
        "payment_count": 1,
        "payment_record": {"status": "SUCCEEDED"},
        "inventory": {"available_quantity": 9},
    }

    monkeypatch.setattr(module, "require_success", lambda *args, **kwargs: committed if "/facts" in args[0] else {"ok": True})
    monkeypatch.setattr(module, "prepare_pending_order", lambda context: (setattr(context, "order_id", "order-001") or {"order_id": "order-001"}))
    monkeypatch.setattr(module, "reset_test_state", lambda context: None)
    monkeypatch.setattr(module, "http_request", lambda *args, **kwargs: (calls.append(1) or HttpResponse(504, {})))

    result = run_business_retry(
        case,
        "http://demo",
        {"ui_version": "v1", "payment_mode": "timeout_after_commit", "product_bug_mode": "off"},
        tmp_path / "after",
    )
    history = json.loads((tmp_path / "after" / "retry_history.json").read_text(encoding="utf-8"))
    assert result["result"] == "PASS"
    assert history["decision"] == "NO_RETRY_ALREADY_COMMITTED"
    assert len(calls) == 1
    assert result["api_facts"]["payment_count"] == 1


def test_report_counts_scenarios_from_result_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-001"
    (run_dir / "cases" / "pass-case").mkdir(parents=True)
    (run_dir / "cases" / "fail-case").mkdir(parents=True)
    run = {
        "run_id": "run-001",
        "suite": "nightly_pay_order",
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:02+00:00",
        "scenarios": [
            {"scenario_id": "pass-case"},
            {"scenario_id": "fail-case"},
        ],
    }
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    for scenario_id, result in (("pass-case", "PASS"), ("fail-case", "FAIL")):
        record = {
            "result": result,
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:01+00:00",
        }
        (run_dir / "cases" / scenario_id / "result.json").write_text(json.dumps(record), encoding="utf-8")
    report = build_report(run_dir, tmp_path / "report.md")
    assert (report["total"], report["passed"], report["failed"]) == (2, 1, 1)
    assert "total: **2**" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_business_assertion_failure_keeps_actual_product_bug_facts(monkeypatch, tmp_path: Path) -> None:
    import skills.assert_business_state as module

    case = _fake_case()
    context = ExecutionContext("http://demo", case, object(), tmp_path, order_id="order-001")
    actual = {
        "order_status": "PAID",
        "payment_count": 1,
        "payment_record": {"status": "SUCCEEDED"},
        "inventory": {"available_quantity": 10},
    }
    monkeypatch.setattr(module, "require_success", lambda *args, **kwargs: actual)
    try:
        assert_business_state(context)
    except SkillError as error:
        assert error.code == "BUSINESS_STATE_ASSERTION_FAILED"
    else:
        raise AssertionError("库存未扣减时必须失败")
    assert context.record["api_facts"]["inventory"]["available_quantity"] == 10

from experiments.failure_classification import run_experiments
from experiments.flaky_automation import run_flaky_experiment
from experiments.shared_state_concurrency import run_shared_state_experiment
from runner.failure_classifier import classify_failure
from runner.stability import FLAKY, INSUFFICIENT_HISTORY, STABLE, classify_stability


PRODUCT_EVIDENCE = {
    "service_reachable": True,
    "app_reachable": True,
    "device_preflight": True,
    "session_created": True,
    "page_reached": True,
    "workflow_started": True,
    "failure_stage": "assert_business_state",
    "failure_skill": "assert_business_state",
    "ui_assertion": "PASS",
    "payment_executed": True,
    "actual_facts": {
        "order_status": "PAID",
        "payment_count": 1,
        "payment_record": {"status": "SUCCEEDED"},
        "inventory": {"available_quantity": 10},
    },
    "expected_facts": {
        "order_status": "PAID",
        "payment_count": 1,
        "payment_record.status": "SUCCEEDED",
        "inventory.available_quantity": 9,
    },
}


def test_failure_category_and_stability_are_separate_dimensions() -> None:
    assert classify_failure(PRODUCT_EVIDENCE)["category"] == "PRODUCT"
    assert FLAKY not in {"PRODUCT", "ENVIRONMENT", "DEVICE", "AUTOMATION"}
    assert classify_stability(["PASS", "FAIL", "PASS", "PASS", "FAIL"]) == FLAKY


def test_same_structured_evidence_is_deterministic_and_ignores_scenario_metadata() -> None:
    first = classify_failure({**PRODUCT_EVIDENCE, "scenario_id": "one", "fault_mode": "product_bug"})
    second = classify_failure({**PRODUCT_EVIDENCE, "scenario_id": "two", "fault_mode": "another-name"})
    assert first == second


def test_automation_locator_failure_is_not_device_failure() -> None:
    evidence = {
        "service_reachable": True,
        "app_reachable": True,
        "device_preflight": True,
        "session_created": True,
        "page_reached": True,
        "workflow_started": True,
        "failure_stage": "locator",
        "failure_skill": "pay_order",
        "payment_executed": False,
        "error": "device unavailable keyword must not control classification",
    }
    assert classify_failure(evidence)["category"] == "AUTOMATION"


def test_environment_and_device_require_structured_stage_evidence() -> None:
    environment = {"service_reachable": False, "app_reachable": False, "failure_stage": "health"}
    device = {
        "service_reachable": True,
        "app_reachable": True,
        "device_preflight": False,
        "session_created": False,
        "failure_stage": "device_preflight",
    }
    assert classify_failure(environment)["category"] == "ENVIRONMENT"
    assert classify_failure(device)["category"] == "DEVICE"


def test_insufficient_or_keyword_only_evidence_is_unclassified() -> None:
    assert classify_failure({"error": "product bug device timeout automation"})["category"] == "UNCLASSIFIED"
    assert classify_failure({"failure_stage": "locator", "error": "device unavailable"})["category"] == "UNCLASSIFIED"


def test_stability_minimum_history_rules() -> None:
    assert classify_stability(["PASS", "PASS"]) == INSUFFICIENT_HISTORY
    assert classify_stability(["PASS"] * 5) == STABLE
    assert classify_stability(["FAIL"] * 5) == STABLE


def test_failure_classification_experiment_produces_all_required_samples(tmp_path) -> None:
    summary = run_experiments(tmp_path / "failure-classification")
    assert {summary["samples"][name]["category"] for name in ("PRODUCT", "AUTOMATION", "ENVIRONMENT", "DEVICE")} == {
        "PRODUCT",
        "AUTOMATION",
        "ENVIRONMENT",
        "DEVICE",
    }
    assert summary["samples"]["UNCLASSIFIED"]["category"] == "UNCLASSIFIED"


def test_flaky_and_shared_state_experiments_are_observable(tmp_path) -> None:
    flaky = run_flaky_experiment(tmp_path / "flaky", tmp_path / "history.jsonl")
    assert flaky["total_runs"] == 12
    assert flaky["pass_count"] > 0
    assert flaky["fail_count"] > 0
    assert flaky["failure_category"] == "AUTOMATION"
    assert flaky["stability"] == FLAKY

    shared = run_shared_state_experiment(tmp_path / "shared" / "summary.json")
    assert shared["result"] == "STATE_CONTAMINATION_OBSERVED"
    assert shared["worker_a"]["timeline"][0]["event"] == "obtained_shared_order"
    assert shared["worker_b"]["timeline"][0]["event"] == "obtained_shared_order"
    assert shared["duplicate_business_action_count"] == 1

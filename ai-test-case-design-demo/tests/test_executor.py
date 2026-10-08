import copy

from app.assets import DEFAULT_ROOT, load, validate_assets
from app.executor import execute_case, execute_cases


def _history():
    return load("history/v1_0_validated_baseline.json")["cases"]


def _targets():
    return load("history/v1_1_additions.json")["cases"]


def test_trusted_history_cases_execute_against_v10():
    report = execute_cases(_history(), "1.0")
    assert (report["total"], report["passed"], report["failed"]) == (32, 32, 0)


def test_all_v11_additions_execute_against_target_rules():
    report = execute_cases(_targets(), "1.1")
    assert report["total"] == len(_targets()) == 15
    assert report["passed"] == report["total"]
    assert report["failed"] == 0


def test_v11_window_boundaries_and_member_level_at_order():
    targets = {case["case_id"]: case for case in _targets()}
    for case_id, outcome in (("H-F13", "accept"), ("H-F07", "accept"), ("H-F08", "reject"),
                             ("H-F18", "accept"), ("H-F19", "accept"), ("H-F20", "reject"), ("H-F21", "accept"),
                             ("H-F09", "accept"), ("H-F10", "reject")):
        assert execute_case(targets[case_id], "1.1")["actual"]["outcome"] == outcome


def test_fast_refund_order_and_failed_qc_recovery():
    targets = {case["case_id"]: case for case in _targets()}
    failed = execute_case(targets["H-F11"], "1.1")["actual"]
    assert failed["sequence"] == ["refund", "qc", "customer_recovery"]
    assert failed["recovery_required"] is True
    for case_id in ("H-F12", "H-F16", "H-F17"):
        assert execute_case(targets[case_id], "1.1")["passed"] is True


def test_changed_expected_value_is_a_real_failure():
    case = copy.deepcopy(_history()[0])
    case["expected"]["outcome"] = "invented_result"
    result = execute_case(case, "1.0")
    assert result["passed"] is False
    assert result["actual"]["outcome"] == "refund_blocked"
    assert result["comparisons"]["outcome"] is False


def test_assets_remain_valid():
    report = validate_assets(DEFAULT_ROOT)
    assert report["status"] == "READY"

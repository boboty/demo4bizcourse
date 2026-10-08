"""主执行者独立验收：人工复算常量与执行报告真实性。"""

import copy
import itertools
import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine import calculate_finance_refund, calculate_finance_sequence, calculate_proportional_refund, execute_v1_0_cases


def order():
    return {
        "items": [{"sku": "A", "gross": "199.00"}, {"sku": "B", "gross": "99.00"}, {"sku": "C", "gross": "59.00"}],
        "promotion": {"enabled": True, "threshold": "300.00", "discount": "50.00"},
        "original_discount": "50.00",
        "paid": "307.00",
    }


@pytest.mark.parametrize("skus,expected", [
    (["A"], "149.00"), (["B"], "49.00"), (["C"], "9.00"),
    (["A", "B"], "248.00"), (["A", "C"], "208.00"),
    (["B", "C"], "108.00"), (["A", "B", "C"], "307.00"),
])
def test_finance_against_hand_calculated_all_subsets(skus, expected):
    assert calculate_finance_refund(order(), return_skus=skus)["refund"] == expected


def test_every_return_order_and_duplicate_conserves_paid_total():
    for permutation in itertools.permutations(["A", "B", "C"]):
        steps = [[sku] for sku in permutation for _ in range(2)]
        rows = calculate_finance_sequence(order(), steps)
        assert sum(Decimal(row["refund"]) for row in rows) == Decimal("307.00")
        assert all(rows[index]["refund"] == "0.00" for index in [1, 3, 5])
        assert all(Decimal(row["refund"]) >= 0 for row in rows)


def test_pass_report_really_compares_expectations():
    path = Path(__file__).resolve().parents[1] / "demo_assets/cases/v1_0_executable.json"
    cases = copy.deepcopy(json.loads(path.read_text(encoding="utf-8")))
    cases["cases"][0]["expected"]["refund"] = "49.00"
    report = execute_v1_0_cases(cases)
    assert (report["total"], report["passed"], report["failed"]) == (20, 19, 1)
    assert report["cases"][0]["actual"]["refund"] == "85.13"
    assert report["cases"][0]["passed"] is False


def test_disabled_promotion_does_not_reject_small_order():
    small = {
        "items": [{"sku": "A", "gross": "20.00"}],
        "promotion": {"enabled": False, "threshold": "300.00", "discount": "50.00"},
        "paid": "20.00",
    }
    assert calculate_finance_refund(small, return_skus=["A"])["refund"] == "20.00"


def test_omitted_discount_uses_promotion_fact_consistently():
    classic = order()
    classic.pop("original_discount")
    classic["return_skus"] = ["B"]
    assert calculate_proportional_refund(classic)["refund"] == "85.13"


def test_executor_must_not_silently_ignore_unimplemented_expectation():
    from app.executor import execute_case

    case = {
        "case_id": "VERIFY-UNIMPLEMENTED-ASSERTION",
        "kind": "eligibility",
        "input": {"member_at_order": "ordinary", "elapsed_seconds": 60},
        "expected": {"outcome": "accept", "unimplemented_assertion": True},
    }
    assert execute_case(case, "1.1")["passed"] is False

import json
from pathlib import Path
from decimal import Decimal

import pytest

from app.engine import calculate_finance_refund, calculate_finance_sequence, calculate_proportional_refund, execute_v1_0_cases


ROOT = Path(__file__).resolve().parents[1]


def load_cases():
    with (ROOT / "demo_assets/cases/v1_0_executable.json").open(encoding="utf-8") as stream:
        return json.load(stream)


def classic_order():
    return {
        "items": [
            {"sku": "A", "gross": "199.00"},
            {"sku": "B", "gross": "99.00"},
            {"sku": "C", "gross": "59.00"},
        ],
        "promotion": {"threshold": "300.00", "discount": "50.00", "enabled": True},
        "original_discount": "50.00",
        "paid": "307.00",
    }


def test_all_twenty_v1_0_cases_execute_and_match_expectations():
    report = execute_v1_0_cases(load_cases())
    assert report["total"] == 20
    assert report["passed"] == 20
    assert report["failed"] == 0
    assert all(row["actual"] == row["expected"] for row in report["cases"])


def test_classic_proportional_assumption_is_85_13():
    order = dict(classic_order(), return_skus=["B"])
    assert calculate_proportional_refund(order) == {"refund": "85.13", "status": "refund_calculated"}


def test_finance_calculation_returns_49_with_auditable_intermediate_values():
    result = calculate_finance_refund(classic_order(), return_skus=["B"])
    assert result == {
        "refund": "49.00",
        "status": "refund_calculated",
        "cumulative_refunded": "49.00",
        "remaining_gross": "258.00",
        "remaining_discount": "0.00",
    }


def test_finance_sequence_b_then_c_then_a_caps_at_paid_and_duplicate_is_noop():
    results = calculate_finance_sequence(classic_order(), [["B"], ["C"], ["A"], ["A"]])
    assert [row["refund"] for row in results] == ["49.00", "59.00", "199.00", "0.00"]
    assert [row["cumulative_refunded"] for row in results[:3]] == ["49.00", "108.00", "307.00"]
    assert results[-1]["status"] == "duplicate_noop"


def test_finance_formula_below_zero_stops_and_requires_manual_review():
    order = {
        "items": [{"sku": "A", "gross": "1.00"}, {"sku": "B", "gross": "299.01"}],
        "promotion": {"threshold": "300.00", "discount": "50.00", "enabled": True},
        "original_discount": "50.00",
        "paid": "250.01",
    }
    result = calculate_finance_refund(order, return_skus=["A"])
    assert result["refund"] == "0.00"
    assert result["status"] == "financial_review_required"
    assert result["formula_due"] == "-49.00"
    assert result["gap"] == "49.00"


@pytest.mark.parametrize(
    "order,returns,expected_message",
    [
        (classic_order(), ["UNKNOWN"], "unknown returned SKU"),
        ({**classic_order(), "paid": "308.00"}, ["B"], "paid does not match"),
    ],
)
def test_finance_rejects_unknown_sku_and_inconsistent_paid(order, returns, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        calculate_finance_refund(order, return_skus=returns)


@pytest.mark.parametrize(
    "gross,enabled,expected_discount",
    [("299.99", True, "0.00"), ("300.00", True, "50.00"), ("300.01", True, "50.00"), ("300.01", False, "0.00")],
)
def test_promotion_threshold_and_enabled_flag(gross, enabled, expected_discount):
    order = {
        "items": [{"sku": "A", "gross": gross}],
        "promotion": {"threshold": "300.00", "discount": "50.00", "enabled": enabled},
        "original_discount": expected_discount,
        "paid": format(Decimal(gross) - Decimal(expected_discount), ".2f"),
    }
    output = calculate_finance_refund(order, return_skus=["A"])
    assert output["refund"] == order["paid"]


def test_proportional_discount_share_rounds_before_subtracting_from_item_price():
    order = {
        "items": [{"sku": "tiny", "gross": "0.04"}, {"sku": "rest", "gross": "399.96"}],
        "promotion": {"threshold": "300.00", "discount": "50.00", "enabled": True},
        "original_discount": "50.00",
        "paid": "350.00",
        "return_skus": ["tiny"],
    }
    assert calculate_proportional_refund(order)["refund"] == "0.03"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_money_values_are_rejected(value):
    order = dict(classic_order(), paid=value)
    with pytest.raises(ValueError, match="finite"):
        calculate_finance_refund(order, return_skus=["B"])

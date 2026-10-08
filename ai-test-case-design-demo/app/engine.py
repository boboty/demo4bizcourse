"""Deterministic money engines used by the classroom demos."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _amount(value: Any, field: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("%s must be a decimal amount" % field) from exc
    if not amount.is_finite():
        raise ValueError("%s must be finite" % field)
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def _order_parts(order: Mapping[str, Any]) -> tuple:
    items = order.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")
    by_sku: Dict[str, Decimal] = {}
    for item in items:
        sku = item.get("sku")
        if not sku or sku in by_sku:
            raise ValueError("item SKUs must be present and unique")
        gross = _amount(item.get("gross"), "item gross")
        if gross < ZERO:
            raise ValueError("item gross cannot be negative")
        by_sku[sku] = gross
    gross_total = sum(by_sku.values(), ZERO).quantize(CENT)
    promo = order.get("promotion") or {}
    threshold = _amount(promo.get("threshold", "300.00"), "promotion threshold")
    discount_value = _amount(promo.get("discount", "50.00"), "promotion discount")
    if threshold <= ZERO:
        raise ValueError("promotion threshold must be positive")
    enabled = bool(promo.get("enabled", False))
    if discount_value < ZERO or (enabled and gross_total >= threshold and discount_value > gross_total):
        raise ValueError("applied promotion discount must be between zero and gross total")
    original_discount = discount_value if enabled and gross_total >= threshold else ZERO
    supplied_discount = _amount(order.get("original_discount", original_discount), "original discount")
    if supplied_discount != original_discount:
        raise ValueError("original_discount does not match promotion inputs")
    paid = _amount(order.get("paid", gross_total - original_discount), "paid")
    if paid < ZERO:
        raise ValueError("paid cannot be negative")
    if paid != gross_total - original_discount:
        raise ValueError("paid does not match item gross less original discount")
    return by_sku, gross_total, threshold, discount_value, enabled, original_discount, paid


def calculate_proportional_refund(order: Mapping[str, Any]) -> Dict[str, str]:
    """Execute the explicit V1.0 proportional-allocation assumption."""
    by_sku, gross_total, _, _, _, original_discount, _ = _order_parts(order)
    returned = order.get("return_skus")
    if not isinstance(returned, list) or not returned:
        raise ValueError("return_skus must be a non-empty list")
    if len(set(returned)) != len(returned):
        raise ValueError("return_skus cannot contain duplicates")
    unknown = set(returned) - set(by_sku)
    if unknown:
        raise ValueError("unknown returned SKU: %s" % sorted(unknown)[0])
    if gross_total == ZERO:
        raise ValueError("gross total must be positive")
    returned_gross = sum((by_sku[sku] for sku in returned), ZERO)
    discount_share = (original_discount * returned_gross / gross_total).quantize(CENT, rounding=ROUND_HALF_UP)
    refund = (returned_gross - discount_share).quantize(CENT, rounding=ROUND_HALF_UP)
    return {"refund": str(refund), "status": "refund_calculated"}


def execute_v1_0_cases(cases: Mapping[str, Any]) -> Dict[str, Any]:
    """Run every case and compare the computed result to its stored expectation."""
    rows: List[Dict[str, Any]] = []
    for case in cases.get("cases", []):
        try:
            actual = calculate_proportional_refund(case["input"])
            expected = case["expected"]
            passed = actual["refund"] == expected.get("refund") and actual["status"] == expected.get("status")
            rows.append({"case_id": case["case_id"], "actual": actual, "expected": {"refund": expected.get("refund"), "status": expected.get("status")}, "passed": passed})
        except (KeyError, TypeError, ValueError) as exc:
            rows.append({"case_id": case.get("case_id", "unknown"), "error": str(exc), "passed": False})
    passed_count = sum(1 for row in rows if row["passed"])
    return {"total": len(rows), "passed": passed_count, "failed": len(rows) - passed_count, "cases": rows}


def calculate_finance_refund(order: Mapping[str, Any], previously_returned_skus: Iterable[str] = (), previously_refunded: Any = "0.00", return_skus: Sequence[str] = ()) -> Dict[str, str]:
    """Apply the independent cumulative finance rule; negative formulae stop for review."""
    by_sku, gross_total, threshold, promo_discount, promo_enabled, original_discount, paid = _order_parts(order)
    prior_skus: Set[str] = set(previously_returned_skus)
    returning = list(return_skus)
    if len(set(returning)) != len(returning):
        raise ValueError("return_skus cannot contain duplicate SKU entries")
    unknown = (prior_skus | set(returning)) - set(by_sku)
    if unknown:
        raise ValueError("unknown returned SKU: %s" % sorted(unknown)[0])
    prior_refund = _amount(previously_refunded, "previously_refunded")
    if prior_refund < ZERO or prior_refund > paid:
        raise ValueError("previously_refunded must be between zero and paid")
    new_skus = set(returning) - prior_skus
    if not new_skus:
        return {"refund": "0.00", "status": "duplicate_noop", "cumulative_refunded": str(prior_refund)}
    all_returned = prior_skus | new_skus
    remaining_gross = sum((amount for sku, amount in by_sku.items() if sku not in all_returned), ZERO)
    remaining_discount = promo_discount if promo_enabled and remaining_gross >= threshold else ZERO
    cumulative_due = paid - (remaining_gross - remaining_discount)
    formula_due = (cumulative_due - prior_refund).quantize(CENT, rounding=ROUND_HALF_UP)
    if formula_due < ZERO:
        return {"refund": "0.00", "status": "financial_review_required", "formula_due": str(formula_due), "gap": str(abs(formula_due)), "remaining_gross": str(remaining_gross), "remaining_discount": str(remaining_discount)}
    refund = min(formula_due, paid - prior_refund).quantize(CENT, rounding=ROUND_HALF_UP)
    cumulative_refunded = (prior_refund + refund).quantize(CENT, rounding=ROUND_HALF_UP)
    return {"refund": str(refund), "status": "refund_calculated", "cumulative_refunded": str(cumulative_refunded), "remaining_gross": str(remaining_gross), "remaining_discount": str(remaining_discount)}


def calculate_finance_sequence(order: Mapping[str, Any], return_sequence: Sequence[Sequence[str]]) -> List[Dict[str, str]]:
    """Apply sequential SKU returns, carrying forward already-returned items and payments."""
    returned: Set[str] = set()
    refunded = ZERO
    result: List[Dict[str, str]] = []
    for skus in return_sequence:
        row = calculate_finance_refund(order, returned, refunded, skus)
        result.append(row)
        if row["status"] == "financial_review_required":
            break
        returned.update(skus)
        refunded = _amount(row.get("cumulative_refunded", refunded), "cumulative_refunded")
    return result

"""Execute trusted historical and target cases against versioned demo rules."""
from typing import Any, Dict, Iterable, List, Mapping

from app.engine import calculate_finance_refund, calculate_finance_sequence


def _money(case: Mapping[str, Any]) -> Dict[str, Any]:
    data = dict(case["input"])
    if isinstance(data.get("items"), dict):
        data["items"] = [{"sku": sku, "gross": amount} for sku, amount in data["items"].items()]
    sequence = data.get("return_sequence")
    if sequence is not None:
        rows = calculate_finance_sequence(data, sequence)
        return {"refund": rows[-1]["refund"], "first_refund": rows[0]["refund"],
                "second_refund": rows[1]["refund"] if len(rows) > 1 else "0.00",
                "cumulative_after_second": rows[1].get("cumulative_refunded", "0.00") if len(rows) > 1 else rows[0].get("cumulative_refunded", "0.00"),
                "status": rows[-1]["status"], "sequence": rows}
    result = calculate_finance_refund(data, data.get("previously_returned_skus", ()),
                                      data.get("previously_refunded", "0.00"), data["return_skus"])
    out = dict(result)
    out["remaining_goods_original"] = result.get("remaining_gross")
    out["recalculated_remaining_discount"] = result.get("remaining_discount")
    return out


def _elapsed(inp: Mapping[str, Any]) -> int:
    if "elapsed_seconds" in inp:
        value = inp["elapsed_seconds"]
    elif "elapsed_hours" in inp:
        value = inp["elapsed_hours"] * 3600
    else:
        raise ValueError("elapsed_hours or elapsed_seconds is required")
    if value < 0:
        raise ValueError("elapsed time cannot be negative")
    return value


def _limit(inp: Mapping[str, Any], version: str) -> int:
    member = inp.get("member_at_order", "ordinary")
    if version == "1.0":
        return 7 * 24 * 3600
    return (15 if member == "gold" else 7) * 24 * 3600


def _eligible(inp: Mapping[str, Any], version: str) -> bool:
    if "elapsed_seconds" not in inp and "elapsed_hours" not in inp:
        return True
    return _elapsed(inp) <= _limit(inp, version)


def _execute_workflow(inp: Mapping[str, Any], version: str) -> Dict[str, Any]:
    if inp.get("decision") == "reject":
        return {"outcome": "application_rejected", "sequence": [], "refund_allowed": False, "recovery_required": False}
    eligible = _eligible(inp, version)
    if "member_at_order" in inp and not eligible:
        return {"outcome": "reject", "sequence": [], "refund_allowed": False, "recovery_required": False}
    fast = version == "1.1" and inp.get("eligible") is True
    has_tracking = bool(inp.get("tracking_no"))
    if fast and not has_tracking:
        return {"outcome": "refund_blocked", "sequence": [], "refund_allowed": False, "recovery_required": False}
    qc = inp.get("qc", "pass")
    if fast:
        sequence = ["refund", "qc"]
        if qc == "fail":
            sequence.append("customer_recovery")
        return {"outcome": "refund_first_then_customer_recovery" if qc == "fail" else "refund_first_qc_pending" if qc == "pending" else "refund_first_then_qc",
                "sequence": sequence, "refund_allowed": True, "recovery_required": qc == "fail"}
    if qc != "pass":
        return {"outcome": "refund_blocked", "sequence": ["qc"], "refund_allowed": False, "recovery_required": False}
    channel = "refund_to_original_balance" if inp.get("payment") == "balance" else "refund_to_original_channel"
    return {"outcome": channel, "sequence": ["qc", "refund"], "refund_allowed": True, "recovery_required": False}


def execute_case(case: Mapping[str, Any], version: str) -> Dict[str, Any]:
    """Return computed actual values and a field-by-field expectation comparison."""
    if version not in ("1.0", "1.1"):
        raise ValueError("version must be '1.0' or '1.1'")
    try:
        kind, inp = case["kind"], case["input"]
        if kind == "money":
            actual = _money(case)
        elif kind in ("workflow", "eligibility"):
            is_time_case = "elapsed_seconds" in inp or "elapsed_hours" in inp
            actual = ({"outcome": "accept" if _eligible(inp, version) else "reject"}
                      if kind == "eligibility" or (is_time_case and "qc" not in inp and "decision" not in inp)
                      else _execute_workflow(inp, version))
        else:
            raise ValueError("unsupported case kind: %s" % kind)
        expected = case["expected"]
        comparisons = {key: key in actual and actual.get(key) == value for key, value in expected.items()}
        passed = bool(comparisons) and all(comparisons.values())
        return {"case_id": case.get("case_id", "unknown"), "actual": actual,
                "expected": dict(expected), "comparisons": comparisons, "passed": passed}
    except (KeyError, TypeError, ValueError) as exc:
        return {"case_id": case.get("case_id", "unknown"), "error": str(exc), "passed": False}


def execute_cases(cases: Iterable[Mapping[str, Any]], version: str) -> Dict[str, Any]:
    rows = [execute_case(case, version) for case in cases]
    passed = sum(row["passed"] for row in rows)
    return {"version": version, "total": len(rows), "passed": passed,
            "failed": len(rows) - passed, "cases": rows}

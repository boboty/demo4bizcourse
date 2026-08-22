from __future__ import annotations


def evaluate_candidate(case: dict) -> dict:
    """Return the selected settlement candidate."""
    refund_ok = bool(case.get("tax_refund_eligible"))
    fx_ok = bool(case.get("fx_loss_eligible"))
    refund = float(case.get("tax_refund_amount", 0))

    if refund_ok:
        return {"mode": "TAX_REFUND_ONLY", "amount": refund}

    if fx_ok:
        return {"mode": "NO_CANDIDATE", "amount": 0.0}

    return {"mode": "NO_CANDIDATE", "amount": 0.0}

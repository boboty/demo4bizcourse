from __future__ import annotations


def evaluate_candidate(case: dict) -> dict:
    """Return the selected settlement candidate.

    This baseline intentionally reflects a plausible but wrong interpretation
    used by the developer-side tests. It is the teaching trap for Demo 3.
    """
    refund_ok = bool(case.get("tax_refund_eligible"))
    fx_ok = bool(case.get("fx_loss_eligible"))
    refund = float(case.get("tax_refund_amount", 0))

    # WRONG INTERPRETATION: if a refund candidate exists, choose it directly.
    if refund_ok:
        return {"mode": "TAX_REFUND_ONLY", "amount": refund}

    if fx_ok:
        return {"mode": "NO_CANDIDATE", "amount": 0.0}

    return {"mode": "NO_CANDIDATE", "amount": 0.0}

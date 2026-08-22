from __future__ import annotations


def evaluate_candidate(case: dict) -> dict:
    """Evaluate combined candidate first; refund-only is a fallback."""
    refund_ok = bool(case.get("tax_refund_eligible"))
    fx_ok = bool(case.get("fx_loss_eligible"))
    excluded = bool(case.get("combined_excluded"))
    refund = float(case.get("tax_refund_amount", 0))
    fx_loss = float(case.get("fx_loss_amount", 0))
    if fx_ok and refund_ok and not excluded:
        return {"mode": "FX_LOSS_PLUS_TAX_REFUND", "amount": fx_loss + refund}
    if refund_ok:
        return {"mode": "TAX_REFUND_ONLY", "amount": refund}
    return {"mode": "NO_CANDIDATE", "amount": 0.0}

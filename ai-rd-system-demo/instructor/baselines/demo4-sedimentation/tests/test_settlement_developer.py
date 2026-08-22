from app.settlement.service import evaluate_candidate


def test_combined_candidate_has_priority_when_not_excluded():
    case = {"fx_loss_eligible": True, "fx_loss_amount": 1200, "tax_refund_eligible": True, "tax_refund_amount": 5000, "combined_excluded": False}
    assert evaluate_candidate(case) == {"mode": "FX_LOSS_PLUS_TAX_REFUND", "amount": 6200.0}


def test_refund_only_is_fallback_when_combined_path_is_excluded():
    case = {"fx_loss_eligible": True, "fx_loss_amount": 1200, "tax_refund_eligible": True, "tax_refund_amount": 5000, "combined_excluded": True}
    assert evaluate_candidate(case) == {"mode": "TAX_REFUND_ONLY", "amount": 5000.0}


def test_refund_only_when_only_refund_is_eligible():
    case = {"fx_loss_eligible": False, "fx_loss_amount": 0, "tax_refund_eligible": True, "tax_refund_amount": 5000, "combined_excluded": False}
    assert evaluate_candidate(case) == {"mode": "TAX_REFUND_ONLY", "amount": 5000.0}


def test_no_candidate_without_refund_eligibility():
    case = {"fx_loss_eligible": True, "fx_loss_amount": 1200, "tax_refund_eligible": False, "tax_refund_amount": 0, "combined_excluded": False}
    assert evaluate_candidate(case) == {"mode": "NO_CANDIDATE", "amount": 0.0}

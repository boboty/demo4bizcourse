"""独立验收后保留的业务测试资产。

covers: AC-001, AC-002, AC-003, AC-004, AC-005
"""

from fastapi.testclient import TestClient

from app.main import create_app


def test_gold_vip100_stacks_only_after_gold_is_evaluated() -> None:
    """covers: AC-004"""
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["membershipDiscount"] == 100
    assert payload["couponDiscount"] == 100
    assert payload["discount"] == 200
    assert payload["finalAmount"] == 1000
    assert "CHECK_GOLD_LEVEL" in payload["decisionTrace"]
    assert "APPLY_GOLD_DISCOUNT" in payload["decisionTrace"]
    assert "APPLY_VIP_COUPON" in payload["decisionTrace"]


def test_gold_discount_is_retained_when_coupon_cannot_stack() -> None:
    """covers: AC-005"""
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["membershipDiscount"] == 100
    assert payload["couponDiscount"] == 0
    assert payload["discount"] == 100
    assert "RETAIN_GOLD_DISCOUNT" in payload["decisionTrace"]


def test_gold_threshold_and_no_discount_boundaries() -> None:
    """covers: AC-001, AC-002"""
    with TestClient(create_app()) as client:
        at_threshold = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "GOLD", "amount": 1000},
        )
        below_threshold = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "GOLD", "amount": 999},
        )

    assert at_threshold.status_code == 200
    assert at_threshold.json()["membershipDiscount"] == 100
    assert below_threshold.status_code == 200
    assert below_threshold.json()["membershipDiscount"] == 0
    assert below_threshold.json()["reason"] == "NO_DISCOUNT"


def test_vip100_coupon_evidence_is_explicit() -> None:
    """covers: AC-003"""
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"},
        )

    assert response.status_code == 200
    assert response.json()["couponDiscount"] == 100


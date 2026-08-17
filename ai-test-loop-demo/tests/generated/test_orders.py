"""AI 第一次生成的接口测试。

covers: AC-001, AC-002, AC-003, AC-005

测试范围覆盖接口合同、常见优惠路径、金额守恒和输入校验，供首次自动化回归使用。
"""

from fastapi.testclient import TestClient

from app.main import create_app


def test_discount_preview_returns_documented_response_shape() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["eligible"] is True
    assert {"discount", "finalAmount", "reason", "decisionTrace"} <= payload.keys()
    assert payload["finalAmount"] == 1000
    assert payload["finalAmount"] + payload["discount"] == 1200


def test_gold_membership_and_vip_coupon_have_individual_contract_evidence() -> None:
    with TestClient(create_app()) as client:
        gold_response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "GOLD", "amount": 1200},
        )
        vip_response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "SILVER", "amount": 600, "coupon": "VIP100"},
        )

    assert gold_response.status_code == 200
    assert gold_response.json()["membershipDiscount"] == 100
    assert vip_response.status_code == 200
    assert vip_response.json()["couponDiscount"] == 100
    assert "CHECK_VIP_COUPON" in vip_response.json()["decisionTrace"]


def test_non_stackable_coupon_keeps_gold_membership_discount() -> None:
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
    assert "RETAIN_GOLD_DISCOUNT" in payload["decisionTrace"]


def test_invalid_customer_level_is_rejected_by_the_contract() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/orders/discount-preview",
            json={"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"},
        )

    assert response.status_code == 422

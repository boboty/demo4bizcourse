"""
Pytest automated tests for POST /api/orders/discount-preview

Target service: http://127.0.0.1:8811 (already running, tested as a black box).

Coverage:
  - AC-1 .. AC-7: the seven acceptance cases from the acceptance-test document,
    each as its own visible test function so there is a 1:1 traceable mapping.
  - Supplementary tests derived directly from the requirement document:
    membership-rule edge cases, coupon/no-coupon equivalence, arithmetic
    invariants, response-contract shape, input validation (422), and
    determinism of repeated calls.
"""

import requests

BASE_URL = "http://127.0.0.1:8811"
ENDPOINT = f"{BASE_URL}/api/orders/discount-preview"

REQUIRED_RESPONSE_FIELDS = {
    "eligible": bool,
    "discount": int,
    "finalAmount": int,
    "membershipDiscount": int,
    "couponDiscount": int,
    "discountSources": list,
    "reason": str,
    "decisionTrace": list,
}


def call_api(payload: dict) -> requests.Response:
    """POST helper against the discount-preview endpoint."""
    return requests.post(ENDPOINT, json=payload, timeout=10)


def assert_response_contract(body: dict) -> None:
    """Every 200 response must contain all required fields with correct types."""
    for field, expected_type in REQUIRED_RESPONSE_FIELDS.items():
        assert field in body, f"missing field '{field}' in response: {body}"
        assert isinstance(body[field], expected_type), (
            f"field '{field}' expected type {expected_type}, "
            f"got {type(body[field])} (value={body[field]!r})"
        )
    for item in body["discountSources"]:
        assert isinstance(item, str)
    for step in body["decisionTrace"]:
        assert isinstance(step, str)


def assert_arithmetic_invariants(payload: dict, body: dict) -> None:
    """Invariants implied by the requirement document, independent of the
    specific rule branch that produced them."""
    assert body["discount"] == body["membershipDiscount"] + body["couponDiscount"]
    assert body["finalAmount"] == payload["amount"] - body["discount"]
    assert body["eligible"] == (body["discount"] > 0)


# ---------------------------------------------------------------------------
# Acceptance cases (AC-1 .. AC-7)
# ---------------------------------------------------------------------------


def test_AC1_gold_1200_no_coupon():
    payload = {"customerLevel": "GOLD", "amount": 1200}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["membershipDiscount"] == 100
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100


def test_AC2_gold_1000_no_coupon():
    payload = {"customerLevel": "GOLD", "amount": 1000}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["membershipDiscount"] == 100


def test_AC3_gold_999_no_coupon():
    payload = {"customerLevel": "GOLD", "amount": 999}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["membershipDiscount"] == 0
    assert body["reason"] == "NO_DISCOUNT"


def test_AC4_standard_600_vip100():
    payload = {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["couponDiscount"] == 100
    assert body["finalAmount"] == 500


def test_AC5_gold_1200_vip100_stacks_with_membership():
    payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["membershipDiscount"] == 100
    assert body["couponDiscount"] == 100
    assert body["discount"] == 200
    assert body["finalAmount"] == 1000
    # Both discount sources should be reflected when they stack.
    assert set(body["discountSources"]) == {"GOLD_MEMBERSHIP", "VIP_COUPON"}


def test_AC6_gold_1200_vip100_no_stack_keeps_membership_only():
    payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["membershipDiscount"] == 100
    assert body["couponDiscount"] == 0
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100
    # Non-stackable coupon must not contribute a separate discount source.
    assert "VIP_COUPON" not in body["discountSources"]
    assert "GOLD_MEMBERSHIP" in body["discountSources"]


def test_AC7_invalid_customer_level_rejected():
    payload = {"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"}
    resp = call_api(payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Supplementary tests derived from the requirement document
# ---------------------------------------------------------------------------


def test_silver_above_threshold_gets_no_membership_discount():
    """Only GOLD qualifies for the membership discount, regardless of amount."""
    payload = {"customerLevel": "SILVER", "amount": 5000}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["membershipDiscount"] == 0
    assert body["eligible"] is False
    assert body["finalAmount"] == 5000


def test_standard_above_threshold_gets_no_membership_discount():
    payload = {"customerLevel": "STANDARD", "amount": 5000}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["membershipDiscount"] == 0
    assert body["eligible"] is False


def test_no_coupon_field_omitted_produces_no_coupon_discount():
    payload = {"customerLevel": "STANDARD", "amount": 600}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["couponDiscount"] == 0
    assert body["discount"] == 0
    assert body["eligible"] is False


def test_coupon_explicit_null_equivalent_to_omitted():
    omitted_payload = {"customerLevel": "GOLD", "amount": 1200}
    null_payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": None}

    resp_omitted = call_api(omitted_payload)
    resp_null = call_api(null_payload)

    assert resp_omitted.status_code == 200
    assert resp_null.status_code == 200

    body_omitted = resp_omitted.json()
    body_null = resp_null.json()

    assert body_omitted["discount"] == body_null["discount"]
    assert body_omitted["finalAmount"] == body_null["finalAmount"]
    assert body_omitted["membershipDiscount"] == body_null["membershipDiscount"]
    assert body_omitted["couponDiscount"] == body_null["couponDiscount"]


def test_amount_zero_is_valid_and_yields_no_discount():
    payload = {"customerLevel": "STANDARD", "amount": 0}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert_response_contract(body)
    assert_arithmetic_invariants(payload, body)

    assert body["finalAmount"] == 0
    assert body["discount"] == 0


def test_negative_amount_rejected():
    payload = {"customerLevel": "GOLD", "amount": -1}
    resp = call_api(payload)
    assert resp.status_code == 422


def test_missing_customer_level_rejected():
    payload = {"amount": 1200}
    resp = call_api(payload)
    assert resp.status_code == 422


def test_missing_amount_rejected():
    payload = {"customerLevel": "GOLD"}
    resp = call_api(payload)
    assert resp.status_code == 422


def test_invalid_coupon_value_rejected():
    payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "NOT_A_REAL_COUPON"}
    resp = call_api(payload)
    assert resp.status_code == 422


def test_response_contract_shape_on_success():
    """All required fields from the OpenAPI contract must be present with
    correct types on a representative successful response."""
    payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
    resp = call_api(payload)
    assert resp.status_code == 200
    body = resp.json()
    assert set(REQUIRED_RESPONSE_FIELDS.keys()).issubset(body.keys())
    assert_response_contract(body)


def test_result_is_deterministic_across_repeated_calls():
    """Same input must always produce the exact same output."""
    payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}

    first = call_api(payload)
    second = call_api(payload)
    third = call_api(payload)

    assert first.status_code == second.status_code == third.status_code == 200
    assert first.json() == second.json() == third.json()

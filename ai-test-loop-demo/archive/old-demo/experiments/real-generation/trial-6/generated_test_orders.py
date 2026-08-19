"""
Pytest automated tests for POST /api/orders/discount-preview.

Scope: black-box HTTP tests against a locally running service at
http://127.0.0.1:8811. Assertions are derived strictly from:
  - the requirements document ("需求：订单优惠预览接口")
  - the acceptance test case table ("验收用例")
  - the OpenAPI contract (DiscountPreviewRequest / DiscountPreviewResponse)

Each acceptance case (#1-#7) has a dedicated test function named
test_ac_<n>_... so failures map back to a specific acceptance row.
"""

import requests
import pytest

BASE_URL = "http://127.0.0.1:8811"
ENDPOINT = f"{BASE_URL}/api/orders/discount-preview"

RESPONSE_FIELDS = {
    "eligible",
    "discount",
    "finalAmount",
    "membershipDiscount",
    "couponDiscount",
    "discountSources",
    "reason",
    "decisionTrace",
}


def call(payload: dict) -> requests.Response:
    """POST the given payload to the discount-preview endpoint."""
    return requests.post(ENDPOINT, json=payload, timeout=10)


def assert_has_full_response_shape(body: dict) -> None:
    """Every 200 response must contain all fields required by the OpenAPI schema."""
    assert RESPONSE_FIELDS.issubset(body.keys()), (
        f"response missing required fields: {RESPONSE_FIELDS - body.keys()}"
    )
    assert isinstance(body["eligible"], bool)
    assert isinstance(body["discount"], int)
    assert isinstance(body["finalAmount"], int)
    assert isinstance(body["membershipDiscount"], int)
    assert isinstance(body["couponDiscount"], int)
    assert isinstance(body["discountSources"], list)
    assert isinstance(body["reason"], str)
    assert isinstance(body["decisionTrace"], list)


# ---------------------------------------------------------------------------
# Acceptance case #1
# customerLevel=GOLD, amount=1200, no coupon
# -> HTTP 200; membershipDiscount=100; discount=100; finalAmount=1100
# ---------------------------------------------------------------------------
def test_ac_1_gold_above_threshold_no_coupon():
    resp = call({"customerLevel": "GOLD", "amount": 1200})
    assert resp.status_code == 200
    body = resp.json()
    assert_has_full_response_shape(body)
    assert body["membershipDiscount"] == 100
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100
    assert body["couponDiscount"] == 0
    assert body["eligible"] is True


# ---------------------------------------------------------------------------
# Acceptance case #2
# customerLevel=GOLD, amount=1000 (boundary, inclusive), no coupon
# -> HTTP 200; membershipDiscount=100
# ---------------------------------------------------------------------------
def test_ac_2_gold_at_threshold_boundary_no_coupon():
    resp = call({"customerLevel": "GOLD", "amount": 1000})
    assert resp.status_code == 200
    body = resp.json()
    assert_has_full_response_shape(body)
    assert body["membershipDiscount"] == 100
    # amount(1000) - discount(100) must equal finalAmount, per requirement semantics
    assert body["discount"] == 100
    assert body["finalAmount"] == 900


# ---------------------------------------------------------------------------
# Acceptance case #3
# customerLevel=GOLD, amount=999 (just below boundary), no coupon
# -> HTTP 200; membershipDiscount=0; reason="NO_DISCOUNT"
# ---------------------------------------------------------------------------
def test_ac_3_gold_below_threshold_boundary_no_coupon():
    resp = call({"customerLevel": "GOLD", "amount": 999})
    assert resp.status_code == 200
    body = resp.json()
    assert_has_full_response_shape(body)
    assert body["membershipDiscount"] == 0
    assert body["reason"] == "NO_DISCOUNT"
    assert body["discount"] == 0
    assert body["couponDiscount"] == 0
    assert body["finalAmount"] == 999
    assert body["eligible"] is False


# ---------------------------------------------------------------------------
# Acceptance case #4
# customerLevel=STANDARD, amount=600, coupon=VIP100
# -> HTTP 200; couponDiscount=100; finalAmount=500
# ---------------------------------------------------------------------------
def test_ac_4_standard_with_vip100_coupon():
    resp = call({"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"})
    assert resp.status_code == 200
    body = resp.json()
    assert_has_full_response_shape(body)
    assert body["couponDiscount"] == 100
    assert body["finalAmount"] == 500
    assert body["membershipDiscount"] == 0
    assert body["discount"] == 100


# ---------------------------------------------------------------------------
# Acceptance case #5
# customerLevel=GOLD, amount=1200, coupon=VIP100
# VIP100 stacks with membership discount -> total 200
# -> HTTP 200; membershipDiscount=100; couponDiscount=100; discount=200; finalAmount=1000
# ---------------------------------------------------------------------------
def test_ac_5_gold_with_vip100_coupon_stacks():
    resp = call({"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"})
    assert resp.status_code == 200
    body = resp.json()
    assert_has_full_response_shape(body)
    assert body["membershipDiscount"] == 100
    assert body["couponDiscount"] == 100
    assert body["discount"] == 200
    assert body["finalAmount"] == 1000


# ---------------------------------------------------------------------------
# Acceptance case #6
# customerLevel=GOLD, amount=1200, coupon=VIP100-NO-STACK
# Membership discount retained, coupon adds nothing extra when membership applies
# -> HTTP 200; membershipDiscount=100; couponDiscount=0; discount=100; finalAmount=1100
# ---------------------------------------------------------------------------
def test_ac_6_gold_with_vip100_no_stack_coupon_does_not_add():
    resp = call({"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"})
    assert resp.status_code == 200
    body = resp.json()
    assert_has_full_response_shape(body)
    assert body["membershipDiscount"] == 100
    assert body["couponDiscount"] == 0
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100


# ---------------------------------------------------------------------------
# Acceptance case #7
# customerLevel=PLATINUM (illegal enum value), amount=1200, coupon=VIP100
# -> HTTP 422
# ---------------------------------------------------------------------------
def test_ac_7_invalid_customer_level_rejected():
    resp = call({"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Supplementary tests: business rules explicitly stated in the requirements
# but not directly covered by an acceptance-case row above.
# ---------------------------------------------------------------------------

def test_no_coupon_field_omitted_is_equivalent_to_no_coupon():
    """Coupon is optional; omitting it entirely must behave the same as no coupon."""
    resp = call({"customerLevel": "GOLD", "amount": 1200})
    assert resp.status_code == 200
    body = resp.json()
    assert body["couponDiscount"] == 0
    assert "VIP_COUPON" not in body["discountSources"]


def test_coupon_explicit_null_is_equivalent_to_no_coupon():
    """coupon: null is an allowed value per the OpenAPI schema and means 'no coupon'."""
    resp = call({"customerLevel": "GOLD", "amount": 1200, "coupon": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["couponDiscount"] == 0
    assert body["membershipDiscount"] == 100
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100


@pytest.mark.parametrize("level", ["SILVER", "STANDARD"])
def test_non_gold_level_never_gets_membership_discount_even_above_threshold(level):
    """Only GOLD qualifies for membership discount, regardless of amount."""
    resp = call({"customerLevel": level, "amount": 5000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 0
    assert "GOLD_MEMBERSHIP" not in body["discountSources"]


def test_vip100_no_stack_still_applies_when_no_membership_discount():
    """
    When the membership condition is NOT met, VIP100-NO-STACK has nothing to
    avoid stacking with, so its own 100-yuan discount must still apply.
    """
    resp = call({"customerLevel": "SILVER", "amount": 1200, "coupon": "VIP100-NO-STACK"})
    assert resp.status_code == 200
    body = resp.json()
    assert_has_full_response_shape(body)
    assert body["membershipDiscount"] == 0
    assert body["couponDiscount"] == 100
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100


def test_no_coupon_no_membership_yields_zero_discount():
    resp = call({"customerLevel": "STANDARD", "amount": 500})
    assert resp.status_code == 200
    body = resp.json()
    assert body["eligible"] is False
    assert body["discount"] == 0
    assert body["membershipDiscount"] == 0
    assert body["couponDiscount"] == 0
    assert body["finalAmount"] == 500
    assert body["reason"] == "NO_DISCOUNT"


def test_final_amount_equals_amount_minus_discount():
    """finalAmount must always equal amount - discount, for a stacking case."""
    amount = 1200
    resp = call({"customerLevel": "GOLD", "amount": amount, "coupon": "VIP100"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount"] == body["membershipDiscount"] + body["couponDiscount"]
    assert body["finalAmount"] == amount - body["discount"]


# ---------------------------------------------------------------------------
# Supplementary tests: input validation per the OpenAPI contract
# (customerLevel enum, amount minimum, coupon enum, required fields).
# ---------------------------------------------------------------------------

def test_negative_amount_rejected():
    resp = call({"customerLevel": "GOLD", "amount": -1})
    assert resp.status_code == 422


def test_zero_amount_is_valid_and_yields_no_discount():
    """amount >= 0 is allowed by the contract; 0 is the minimum valid value."""
    resp = call({"customerLevel": "GOLD", "amount": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount"] == 0
    assert body["finalAmount"] == 0


def test_missing_customer_level_rejected():
    resp = call({"amount": 1200})
    assert resp.status_code == 422


def test_missing_amount_rejected():
    resp = call({"customerLevel": "GOLD"})
    assert resp.status_code == 422


def test_invalid_coupon_value_rejected():
    resp = call({"customerLevel": "GOLD", "amount": 1200, "coupon": "FAKE100"})
    assert resp.status_code == 422


@pytest.mark.parametrize("level", ["", "gold", "Gold", "GOLD ", 123, None])
def test_malformed_customer_level_values_rejected(level):
    resp = call({"customerLevel": level, "amount": 1200})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Supplementary test: determinism, as explicitly required by the spec
# ("计算结果需保证确定性：相同输入永远得到相同输出").
# ---------------------------------------------------------------------------

def test_response_is_deterministic_across_repeated_calls():
    payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
    first = call(payload)
    second = call(payload)
    third = call(payload)

    assert first.status_code == second.status_code == third.status_code == 200
    assert first.json() == second.json() == third.json()

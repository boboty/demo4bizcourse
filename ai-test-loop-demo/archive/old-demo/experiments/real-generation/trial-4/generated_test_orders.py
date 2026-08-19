"""
Pytest automated tests for POST /api/orders/discount-preview

Target service (must already be running locally): http://127.0.0.1:8811

These tests treat the service as a black box: they only rely on the
published requirements doc, the acceptance-case table, and the OpenAPI
contract for the endpoint. HTTP calls are made with the `requests`
library.
"""

from __future__ import annotations

import copy

import pytest
import requests

BASE_URL = "http://127.0.0.1:8811"
ENDPOINT = f"{BASE_URL}/api/orders/discount-preview"

REQUIRED_RESPONSE_FIELDS = {
    "eligible",
    "discount",
    "finalAmount",
    "membershipDiscount",
    "couponDiscount",
    "discountSources",
    "reason",
    "decisionTrace",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def post_discount_preview(payload: dict) -> requests.Response:
    """POST the given JSON payload to the discount-preview endpoint."""
    return requests.post(ENDPOINT, json=payload, timeout=10)


def assert_contract_shape(body: dict) -> None:
    """Validate the response against the OpenAPI-documented contract:
    all required fields present, with the documented types.
    """
    assert REQUIRED_RESPONSE_FIELDS.issubset(body.keys()), (
        f"Response missing required fields: "
        f"{REQUIRED_RESPONSE_FIELDS - body.keys()}"
    )

    assert isinstance(body["eligible"], bool)
    assert isinstance(body["discount"], int) and not isinstance(body["discount"], bool)
    assert isinstance(body["finalAmount"], int) and not isinstance(
        body["finalAmount"], bool
    )
    assert isinstance(body["membershipDiscount"], int) and not isinstance(
        body["membershipDiscount"], bool
    )
    assert isinstance(body["couponDiscount"], int) and not isinstance(
        body["couponDiscount"], bool
    )
    assert isinstance(body["discountSources"], list)
    assert all(isinstance(item, str) for item in body["discountSources"])
    assert isinstance(body["reason"], str) and body["reason"] != ""
    assert isinstance(body["decisionTrace"], list)
    assert all(isinstance(item, str) for item in body["decisionTrace"])


def assert_business_invariants(body: dict) -> None:
    """Cross-field invariants implied by the requirements doc:
    - discount is exactly the sum of membership + coupon discount
    - finalAmount is amount minus discount (checked by caller when amount known)
    - eligible is true iff a non-zero discount was produced
    """
    assert body["discount"] == body["membershipDiscount"] + body["couponDiscount"]
    assert body["eligible"] == (body["discount"] > 0)
    assert body["discount"] >= 0
    assert body["membershipDiscount"] >= 0
    assert body["couponDiscount"] >= 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def ensure_service_available():
    """Fail fast with a clear message if the service isn't reachable."""
    try:
        requests.post(
            ENDPOINT,
            json={"customerLevel": "STANDARD", "amount": 0},
            timeout=5,
        )
    except requests.exceptions.ConnectionError as exc:
        pytest.fail(
            f"Could not reach discount-preview service at {BASE_URL}. "
            f"Is it running? Original error: {exc}"
        )


# ---------------------------------------------------------------------------
# Acceptance cases (from the acceptance-case table, one test per row)
# ---------------------------------------------------------------------------


class TestAcceptanceCases:
    """One test per row of the business-provided acceptance table."""

    def test_case_1_gold_1200_no_coupon(self):
        resp = post_discount_preview({"customerLevel": "GOLD", "amount": 1200})
        assert resp.status_code == 200
        body = resp.json()
        assert_contract_shape(body)
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 100
        assert body["discount"] == 100
        assert body["finalAmount"] == 1100

    def test_case_2_gold_1000_no_coupon(self):
        resp = post_discount_preview({"customerLevel": "GOLD", "amount": 1000})
        assert resp.status_code == 200
        body = resp.json()
        assert_contract_shape(body)
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 100

    def test_case_3_gold_999_no_coupon(self):
        resp = post_discount_preview({"customerLevel": "GOLD", "amount": 999})
        assert resp.status_code == 200
        body = resp.json()
        assert_contract_shape(body)
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 0
        assert body["reason"] == "NO_DISCOUNT"

    def test_case_4_standard_600_vip100(self):
        resp = post_discount_preview(
            {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_contract_shape(body)
        assert_business_invariants(body)
        assert body["couponDiscount"] == 100
        assert body["finalAmount"] == 500

    def test_case_5_gold_1200_vip100_stacks(self):
        resp = post_discount_preview(
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_contract_shape(body)
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 100
        assert body["couponDiscount"] == 100
        assert body["discount"] == 200
        assert body["finalAmount"] == 1000

    def test_case_6_gold_1200_vip100_no_stack(self):
        resp = post_discount_preview(
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_contract_shape(body)
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 100
        assert body["couponDiscount"] == 0
        assert body["discount"] == 100
        assert body["finalAmount"] == 1100

    def test_case_7_invalid_customer_level_rejected(self):
        resp = post_discount_preview(
            {"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"}
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Membership discount rule: boundary and level-scoping behavior
# ---------------------------------------------------------------------------


class TestMembershipDiscountRule:
    def test_gold_below_threshold_amount_998_no_membership_discount(self):
        resp = post_discount_preview({"customerLevel": "GOLD", "amount": 998})
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 0
        assert body["eligible"] is False
        assert body["finalAmount"] == 998

    def test_silver_high_amount_no_membership_discount(self):
        """Only GOLD gets the membership discount, regardless of amount."""
        resp = post_discount_preview({"customerLevel": "SILVER", "amount": 5000})
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 0
        assert body["eligible"] is False
        assert body["finalAmount"] == 5000

    def test_standard_high_amount_no_membership_discount(self):
        """Only GOLD gets the membership discount, regardless of amount."""
        resp = post_discount_preview({"customerLevel": "STANDARD", "amount": 5000})
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 0
        assert body["eligible"] is False
        assert body["finalAmount"] == 5000

    def test_standard_amount_zero_no_discount(self):
        resp = post_discount_preview({"customerLevel": "STANDARD", "amount": 0})
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["eligible"] is False
        assert body["discount"] == 0
        assert body["finalAmount"] == 0
        assert body["reason"] == "NO_DISCOUNT"


# ---------------------------------------------------------------------------
# Coupon rules: applicability independent of membership eligibility, and
# the stacking vs non-stacking behavior explicitly.
# ---------------------------------------------------------------------------


class TestCouponRules:
    def test_no_coupon_field_omitted_produces_no_coupon_discount(self):
        resp = post_discount_preview({"customerLevel": "STANDARD", "amount": 600})
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["couponDiscount"] == 0

    def test_coupon_explicit_null_produces_no_coupon_discount(self):
        resp = post_discount_preview(
            {"customerLevel": "GOLD", "amount": 1200, "coupon": None}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["couponDiscount"] == 0
        assert body["membershipDiscount"] == 100

    def test_vip100_applies_even_when_membership_condition_not_met(self):
        """VIP100 gives 100 discount on its own, independent of whether the
        GOLD membership condition (amount >= 1000) is satisfied."""
        resp = post_discount_preview(
            {"customerLevel": "GOLD", "amount": 500, "coupon": "VIP100"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 0
        assert body["couponDiscount"] == 100
        assert body["discount"] == 100
        assert body["finalAmount"] == 400

    def test_vip100_no_stack_applies_even_when_membership_condition_not_met(self):
        """When membership discount does NOT apply, VIP100-NO-STACK still
        grants its own 100 discount (non-stacking only matters when both
        would otherwise apply)."""
        resp = post_discount_preview(
            {"customerLevel": "GOLD", "amount": 500, "coupon": "VIP100-NO-STACK"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 0
        assert body["couponDiscount"] == 100
        assert body["discount"] == 100
        assert body["finalAmount"] == 400

    def test_vip100_on_silver_ineligible_for_membership_discount(self):
        """Coupon discount applies for non-GOLD levels too, without a
        membership discount stacking on top."""
        resp = post_discount_preview(
            {"customerLevel": "SILVER", "amount": 2000, "coupon": "VIP100"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 0
        assert body["couponDiscount"] == 100
        assert body["discount"] == 100
        assert body["finalAmount"] == 1900

    @pytest.mark.parametrize(
        "coupon,expected_coupon_discount",
        [
            ("VIP100", 100),
            ("VIP100-NO-STACK", 0),
        ],
    )
    def test_stacking_behavior_when_membership_condition_met(
        self, coupon, expected_coupon_discount
    ):
        resp = post_discount_preview(
            {"customerLevel": "GOLD", "amount": 1500, "coupon": coupon}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert_business_invariants(body)
        assert body["membershipDiscount"] == 100
        assert body["couponDiscount"] == expected_coupon_discount


# ---------------------------------------------------------------------------
# Input validation: rejection of illegal / malformed input
# ---------------------------------------------------------------------------


class TestInputValidation:
    @pytest.mark.parametrize(
        "invalid_level",
        ["PLATINUM", "gold", "silver", "standard", "", "VIP"],
    )
    def test_invalid_customer_level_rejected(self, invalid_level):
        resp = post_discount_preview(
            {"customerLevel": invalid_level, "amount": 1000}
        )
        assert resp.status_code == 422

    def test_negative_amount_rejected(self):
        resp = post_discount_preview({"customerLevel": "GOLD", "amount": -5})
        assert resp.status_code == 422

    def test_non_integer_amount_rejected(self):
        resp = post_discount_preview({"customerLevel": "GOLD", "amount": 1200.5})
        assert resp.status_code == 422

    def test_missing_customer_level_rejected(self):
        resp = post_discount_preview({"amount": 1200})
        assert resp.status_code == 422

    def test_missing_amount_rejected(self):
        resp = post_discount_preview({"customerLevel": "GOLD"})
        assert resp.status_code == 422

    def test_empty_body_rejected(self):
        resp = post_discount_preview({})
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "invalid_coupon",
        ["RANDOM", "vip100", "VIP200", "VIP100_NO_STACK"],
    )
    def test_invalid_coupon_value_rejected(self, invalid_coupon):
        resp = post_discount_preview(
            {"customerLevel": "GOLD", "amount": 1200, "coupon": invalid_coupon}
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Determinism: identical input must always produce identical output.
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.parametrize(
        "payload",
        [
            {"customerLevel": "GOLD", "amount": 1200},
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"},
            {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"},
            {"customerLevel": "GOLD", "amount": 999},
        ],
    )
    def test_repeated_calls_return_identical_response(self, payload):
        responses = [
            post_discount_preview(copy.deepcopy(payload)).json() for _ in range(3)
        ]
        assert all(r == responses[0] for r in responses), (
            f"Non-deterministic responses for payload {payload}: {responses}"
        )


# ---------------------------------------------------------------------------
# General contract validation across a spread of representative inputs.
# ---------------------------------------------------------------------------


class TestResponseContract:
    @pytest.mark.parametrize(
        "payload",
        [
            {"customerLevel": "GOLD", "amount": 1200},
            {"customerLevel": "GOLD", "amount": 1000},
            {"customerLevel": "GOLD", "amount": 999},
            {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"},
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"},
            {"customerLevel": "SILVER", "amount": 0},
        ],
    )
    def test_response_matches_openapi_contract(self, payload):
        resp = post_discount_preview(payload)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        body = resp.json()
        assert_contract_shape(body)
        assert_business_invariants(body)
        # finalAmount must equal amount minus total discount.
        assert body["finalAmount"] == payload["amount"] - body["discount"]

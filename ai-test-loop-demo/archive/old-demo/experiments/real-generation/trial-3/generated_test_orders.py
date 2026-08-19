"""
Pytest automated tests for POST /api/orders/discount-preview

Target service (already running, tested as a black box):
    http://127.0.0.1:8811

Covers:
  - All 7 business acceptance cases from the acceptance-test document.
  - Response schema conformance against the provided OpenAPI contract.
  - Core business invariants stated in the requirements doc:
      discount == membershipDiscount + couponDiscount
      finalAmount == amount - discount
      eligible == (discount > 0)
  - Validation/rejection behavior for illegal input (per OpenAPI contract:
    customerLevel enum, amount >= 0 integer, coupon enum).
  - Determinism: identical input always yields an identical response.
"""

import requests
import pytest

BASE_URL = "http://127.0.0.1:8811"
ENDPOINT = f"{BASE_URL}/api/orders/discount-preview"
TIMEOUT = 5

REQUIRED_FIELDS = {
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
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _ensure_service_reachable():
    """Fail fast with a clear message if the target service isn't up."""
    try:
        requests.post(
            ENDPOINT,
            json={"customerLevel": "STANDARD", "amount": 0},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError as exc:
        pytest.fail(
            f"Cannot reach {ENDPOINT}. Is the service running on "
            f"127.0.0.1:8811? Original error: {exc}"
        )


def call_api(payload):
    """POST the given JSON payload to the discount-preview endpoint."""
    return requests.post(ENDPOINT, json=payload, timeout=TIMEOUT)


def assert_valid_response_schema(data):
    """Validate the response body against the DiscountPreviewResponse
    schema defined in the OpenAPI contract (required fields + types)."""
    assert REQUIRED_FIELDS.issubset(data.keys()), (
        f"Response missing required fields. Got keys: {sorted(data.keys())}"
    )
    assert isinstance(data["eligible"], bool)
    assert isinstance(data["discount"], int)
    assert isinstance(data["finalAmount"], int)
    assert isinstance(data["membershipDiscount"], int)
    assert isinstance(data["couponDiscount"], int)
    assert isinstance(data["reason"], str)
    assert isinstance(data["discountSources"], list)
    assert all(isinstance(item, str) for item in data["discountSources"])
    assert isinstance(data["decisionTrace"], list)
    assert all(isinstance(item, str) for item in data["decisionTrace"])


def assert_business_invariants(data, amount):
    """Cross-field invariants implied by the requirements document:
      - discount is the sum of the two discount components
      - finalAmount is amount minus the total discount
      - eligible reflects whether any discount was produced
      - the number of discount sources matches the number of
        discount components that actually contributed (>0)
    """
    assert data["discount"] == data["membershipDiscount"] + data["couponDiscount"], (
        "discount must equal membershipDiscount + couponDiscount"
    )
    assert data["finalAmount"] == amount - data["discount"], (
        "finalAmount must equal amount - discount"
    )
    assert data["eligible"] == (data["discount"] > 0), (
        "eligible must be true iff discount > 0"
    )

    expected_source_count = (1 if data["membershipDiscount"] > 0 else 0) + (
        1 if data["couponDiscount"] > 0 else 0
    )
    assert len(data["discountSources"]) == expected_source_count, (
        f"discountSources length ({len(data['discountSources'])}) does not match "
        f"number of active discount components ({expected_source_count})"
    )


def assert_full_response(resp, amount, expected_status=200):
    assert resp.status_code == expected_status, (
        f"expected HTTP {expected_status}, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert_valid_response_schema(data)
    assert_business_invariants(data, amount)
    return data


# ---------------------------------------------------------------------------
# Acceptance cases (business-provided table, cases 1-7)
# ---------------------------------------------------------------------------

class TestAcceptanceCases:
    """One test per row of the acceptance-test document."""

    def test_case1_gold_1200_no_coupon(self):
        payload = {"customerLevel": "GOLD", "amount": 1200}
        data = assert_full_response(call_api(payload), amount=1200)
        assert data["membershipDiscount"] == 100
        assert data["discount"] == 100
        assert data["finalAmount"] == 1100

    def test_case2_gold_1000_no_coupon_threshold_inclusive(self):
        payload = {"customerLevel": "GOLD", "amount": 1000}
        data = assert_full_response(call_api(payload), amount=1000)
        assert data["membershipDiscount"] == 100

    def test_case3_gold_999_no_coupon_below_threshold(self):
        payload = {"customerLevel": "GOLD", "amount": 999}
        data = assert_full_response(call_api(payload), amount=999)
        assert data["membershipDiscount"] == 0
        assert data["reason"] == "NO_DISCOUNT"

    def test_case4_standard_600_vip100(self):
        payload = {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"}
        data = assert_full_response(call_api(payload), amount=600)
        assert data["couponDiscount"] == 100
        assert data["finalAmount"] == 500

    def test_case5_gold_1200_vip100_stacks_with_membership(self):
        payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
        data = assert_full_response(call_api(payload), amount=1200)
        assert data["membershipDiscount"] == 100
        assert data["couponDiscount"] == 100
        assert data["discount"] == 200
        assert data["finalAmount"] == 1000

    def test_case6_gold_1200_vip100_no_stack(self):
        payload = {
            "customerLevel": "GOLD",
            "amount": 1200,
            "coupon": "VIP100-NO-STACK",
        }
        data = assert_full_response(call_api(payload), amount=1200)
        assert data["membershipDiscount"] == 100
        assert data["couponDiscount"] == 0
        assert data["discount"] == 100
        assert data["finalAmount"] == 1100

    def test_case7_invalid_customer_level_rejected(self):
        payload = {"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"}
        resp = call_api(payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Additional membership-rule coverage (derived directly from requirements doc)
# ---------------------------------------------------------------------------

class TestMembershipRule:
    """Only GOLD + amount >= 1000 grants the membership discount; every
    other level/amount combination must yield membershipDiscount == 0."""

    @pytest.mark.parametrize(
        "level,amount",
        [
            ("SILVER", 2000),
            ("STANDARD", 2000),
            ("SILVER", 1000),
            ("STANDARD", 1000),
        ],
    )
    def test_non_gold_never_gets_membership_discount(self, level, amount):
        payload = {"customerLevel": level, "amount": amount}
        data = assert_full_response(call_api(payload), amount=amount)
        assert data["membershipDiscount"] == 0
        assert data["reason"] == "NO_DISCOUNT"

    def test_amount_zero_standard_no_discount(self):
        payload = {"customerLevel": "STANDARD", "amount": 0}
        data = assert_full_response(call_api(payload), amount=0)
        assert data["eligible"] is False
        assert data["discount"] == 0
        assert data["finalAmount"] == 0


# ---------------------------------------------------------------------------
# Additional coupon-rule coverage
# ---------------------------------------------------------------------------

class TestCouponRule:
    def test_no_coupon_field_omitted_produces_no_coupon_discount(self):
        payload = {"customerLevel": "STANDARD", "amount": 600}
        data = assert_full_response(call_api(payload), amount=600)
        assert data["couponDiscount"] == 0

    def test_coupon_explicit_null_equivalent_to_no_coupon(self):
        payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": None}
        data = assert_full_response(call_api(payload), amount=1200)
        assert data["couponDiscount"] == 0
        assert data["membershipDiscount"] == 100
        assert data["discount"] == 100

    def test_vip100_without_membership_condition_still_applies(self):
        # SILVER never qualifies for membership discount, so VIP100 should
        # apply on its own with no stacking conflict.
        payload = {"customerLevel": "SILVER", "amount": 1200, "coupon": "VIP100"}
        data = assert_full_response(call_api(payload), amount=1200)
        assert data["membershipDiscount"] == 0
        assert data["couponDiscount"] == 100
        assert data["discount"] == 100

    def test_vip100_no_stack_without_membership_condition_still_applies(self):
        # The "no-stack" behavior only suppresses the coupon when it would
        # otherwise combine with an active membership discount. With no
        # membership discount in play, VIP100-NO-STACK should behave the
        # same as VIP100.
        payload = {
            "customerLevel": "SILVER",
            "amount": 1200,
            "coupon": "VIP100-NO-STACK",
        }
        data = assert_full_response(call_api(payload), amount=1200)
        assert data["membershipDiscount"] == 0
        assert data["couponDiscount"] == 100
        assert data["discount"] == 100


# ---------------------------------------------------------------------------
# Input validation (grounded in the OpenAPI request schema)
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_missing_customer_level_rejected(self):
        resp = call_api({"amount": 1200})
        assert resp.status_code == 422

    def test_missing_amount_rejected(self):
        resp = call_api({"customerLevel": "GOLD"})
        assert resp.status_code == 422

    def test_negative_amount_rejected(self):
        resp = call_api({"customerLevel": "STANDARD", "amount": -1})
        assert resp.status_code == 422

    def test_non_integer_amount_rejected(self):
        resp = call_api({"customerLevel": "GOLD", "amount": 1200.5})
        assert resp.status_code == 422

    def test_invalid_coupon_value_rejected(self):
        resp = call_api(
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "RANDOM-COUPON"}
        )
        assert resp.status_code == 422

    def test_customer_level_is_case_sensitive(self):
        resp = call_api({"customerLevel": "gold", "amount": 1200})
        assert resp.status_code == 422

    @pytest.mark.parametrize("level", ["", "GOLDEN", "gold ", "Gold"])
    def test_various_invalid_customer_levels_rejected(self, level):
        resp = call_api({"customerLevel": level, "amount": 1200})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Determinism: identical input must always produce an identical response
# ---------------------------------------------------------------------------

class TestDeterminism:
    @pytest.mark.parametrize(
        "payload",
        [
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"},
            {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"},
            {"customerLevel": "GOLD", "amount": 999},
        ],
        ids=["gold-vip100", "gold-no-stack", "standard-vip100", "gold-below-threshold"],
    )
    def test_repeated_calls_return_identical_response(self, payload):
        responses = [call_api(payload) for _ in range(3)]
        for resp in responses:
            assert resp.status_code == 200
        bodies = [resp.json() for resp in responses]
        first = bodies[0]
        for body in bodies[1:]:
            assert body == first, "Identical input must yield identical output"

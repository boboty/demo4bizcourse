"""
Pytest automated tests for POST /api/orders/discount-preview

Target service (must already be running locally):
    http://127.0.0.1:8811

Covers:
  - All 7 acceptance-criteria rows from the acceptance-case document.
  - Supplementary boundary / validation / determinism checks derived from
    the requirements document and the OpenAPI contract.

Run with:
    pytest generated_test_orders.py -v
"""

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8811"
ENDPOINT = "/api/orders/discount-preview"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


def post_preview(client, payload):
    return client.post(ENDPOINT, json=payload)


# ---------------------------------------------------------------------------
# Acceptance cases (AC-1 .. AC-7)
# ---------------------------------------------------------------------------


def test_ac1_gold_amount_1200_no_coupon(client):
    """AC-1: GOLD, amount=1200, no coupon -> 200; membershipDiscount=100;
    discount=100; finalAmount=1100."""
    resp = post_preview(client, {"customerLevel": "GOLD", "amount": 1200})
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 100
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100
    assert body["couponDiscount"] == 0
    assert body["eligible"] is True


def test_ac2_gold_amount_1000_boundary_no_coupon(client):
    """AC-2: GOLD, amount=1000 (boundary, inclusive), no coupon -> 200;
    membershipDiscount=100."""
    resp = post_preview(client, {"customerLevel": "GOLD", "amount": 1000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 100


def test_ac3_gold_amount_999_below_threshold_no_coupon(client):
    """AC-3: GOLD, amount=999 (just below threshold), no coupon -> 200;
    membershipDiscount=0; reason="NO_DISCOUNT"."""
    resp = post_preview(client, {"customerLevel": "GOLD", "amount": 999})
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 0
    assert body["reason"] == "NO_DISCOUNT"


def test_ac4_standard_amount_600_with_vip100(client):
    """AC-4: STANDARD, amount=600, coupon=VIP100 -> 200; couponDiscount=100;
    finalAmount=500."""
    resp = post_preview(
        client, {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["couponDiscount"] == 100
    assert body["finalAmount"] == 500


def test_ac5_gold_amount_1200_with_vip100_stacks(client):
    """AC-5: GOLD, amount=1200, coupon=VIP100 -> 200; membershipDiscount=100;
    couponDiscount=100; discount=200 (stacked); finalAmount=1000."""
    resp = post_preview(
        client, {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 100
    assert body["couponDiscount"] == 100
    assert body["discount"] == 200
    assert body["finalAmount"] == 1000


def test_ac6_gold_amount_1200_with_vip100_no_stack(client):
    """AC-6: GOLD, amount=1200, coupon=VIP100-NO-STACK -> 200;
    membershipDiscount=100; couponDiscount=0 (not stacked); discount=100;
    finalAmount=1100."""
    resp = post_preview(
        client,
        {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 100
    assert body["couponDiscount"] == 0
    assert body["discount"] == 100
    assert body["finalAmount"] == 1100


def test_ac7_invalid_customer_level_rejected(client):
    """AC-7: customerLevel=PLATINUM (invalid), amount=1200, coupon=VIP100 ->
    422 (rejected by the API)."""
    resp = post_preview(
        client, {"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Supplementary tests: response schema / field presence (per OpenAPI contract)
# ---------------------------------------------------------------------------


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


def test_response_contains_all_required_fields_with_correct_types(client):
    resp = post_preview(client, {"customerLevel": "GOLD", "amount": 1200})
    assert resp.status_code == 200
    body = resp.json()

    assert REQUIRED_RESPONSE_FIELDS.issubset(body.keys())
    assert isinstance(body["eligible"], bool)
    assert isinstance(body["discount"], int)
    assert isinstance(body["finalAmount"], int)
    assert isinstance(body["membershipDiscount"], int)
    assert isinstance(body["couponDiscount"], int)
    assert isinstance(body["discountSources"], list)
    assert all(isinstance(item, str) for item in body["discountSources"])
    assert isinstance(body["reason"], str)
    assert isinstance(body["decisionTrace"], list)
    assert all(isinstance(item, str) for item in body["decisionTrace"])


def test_response_content_type_is_json(client):
    resp = post_preview(client, {"customerLevel": "STANDARD", "amount": 100})
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")


def test_discount_equals_sum_of_membership_and_coupon_discount(client):
    """discount should always equal membershipDiscount + couponDiscount,
    and finalAmount should equal amount - discount."""
    amount = 1200
    resp = post_preview(
        client, {"customerLevel": "GOLD", "amount": amount, "coupon": "VIP100"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount"] == body["membershipDiscount"] + body["couponDiscount"]
    assert body["finalAmount"] == amount - body["discount"]


# ---------------------------------------------------------------------------
# Supplementary tests: membership discount rule boundaries
# ---------------------------------------------------------------------------


def test_silver_level_never_gets_membership_discount(client):
    resp = post_preview(client, {"customerLevel": "SILVER", "amount": 5000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 0


def test_standard_level_never_gets_membership_discount(client):
    resp = post_preview(client, {"customerLevel": "STANDARD", "amount": 5000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 0


def test_gold_amount_zero_no_membership_discount(client):
    resp = post_preview(client, {"customerLevel": "GOLD", "amount": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 0
    assert body["discount"] == 0
    assert body["finalAmount"] == 0
    assert body["eligible"] is False


def test_no_discount_when_nothing_applies(client):
    resp = post_preview(client, {"customerLevel": "STANDARD", "amount": 100})
    assert resp.status_code == 200
    body = resp.json()
    assert body["eligible"] is False
    assert body["discount"] == 0
    assert body["finalAmount"] == 100
    assert body["discountSources"] == []
    assert body["reason"] == "NO_DISCOUNT"


# ---------------------------------------------------------------------------
# Supplementary tests: coupon rule interactions
# ---------------------------------------------------------------------------


def test_vip100_applies_alone_when_membership_not_eligible(client):
    """GOLD but below the amount threshold: membership discount is 0, but
    VIP100 coupon should still independently apply its own 100 discount."""
    resp = post_preview(
        client, {"customerLevel": "GOLD", "amount": 999, "coupon": "VIP100"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 0
    assert body["couponDiscount"] == 100
    assert body["discount"] == 100
    assert body["finalAmount"] == 899


def test_vip100_no_stack_applies_alone_when_membership_not_eligible(client):
    """When membership discount does not apply, VIP100-NO-STACK still grants
    its own 100 discount (non-stacking only matters when both would fire)."""
    resp = post_preview(
        client,
        {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100-NO-STACK"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["membershipDiscount"] == 0
    assert body["couponDiscount"] == 100
    assert body["discount"] == 100
    assert body["finalAmount"] == 500


def test_no_coupon_field_omitted_behaves_like_no_coupon(client):
    resp_omitted = post_preview(client, {"customerLevel": "GOLD", "amount": 1200})
    resp_explicit_null = post_preview(
        client, {"customerLevel": "GOLD", "amount": 1200, "coupon": None}
    )
    assert resp_omitted.status_code == 200
    assert resp_explicit_null.status_code == 200
    body_omitted = resp_omitted.json()
    body_null = resp_explicit_null.json()
    assert body_omitted["couponDiscount"] == 0
    assert body_null["couponDiscount"] == 0
    assert body_omitted["discount"] == body_null["discount"]
    assert body_omitted["finalAmount"] == body_null["finalAmount"]


@pytest.mark.parametrize(
    "customer_level,amount,coupon,expected_discount,expected_final",
    [
        ("GOLD", 1200, None, 100, 1100),
        ("GOLD", 1000, None, 100, 900),
        ("GOLD", 999, None, 0, 999),
        ("STANDARD", 600, "VIP100", 100, 500),
        ("GOLD", 1200, "VIP100", 200, 1000),
        ("GOLD", 1200, "VIP100-NO-STACK", 100, 1100),
    ],
)
def test_discount_matrix(
    client, customer_level, amount, coupon, expected_discount, expected_final
):
    """Parametrized re-check of the acceptance discount/finalAmount matrix,
    consolidated for quick regression coverage."""
    payload = {"customerLevel": customer_level, "amount": amount}
    if coupon is not None:
        payload["coupon"] = coupon
    resp = post_preview(client, payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount"] == expected_discount
    assert body["finalAmount"] == expected_final


# ---------------------------------------------------------------------------
# Supplementary tests: input validation (400/422 rejection paths)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("invalid_level", ["PLATINUM", "gold", "", "Gold", "BRONZE"])
def test_invalid_customer_level_values_rejected(client, invalid_level):
    resp = post_preview(
        client, {"customerLevel": invalid_level, "amount": 1000}
    )
    assert resp.status_code == 422


def test_missing_customer_level_rejected(client):
    resp = post_preview(client, {"amount": 1200})
    assert resp.status_code == 422


def test_missing_amount_rejected(client):
    resp = post_preview(client, {"customerLevel": "GOLD"})
    assert resp.status_code == 422


def test_negative_amount_rejected(client):
    resp = post_preview(client, {"customerLevel": "GOLD", "amount": -1})
    assert resp.status_code == 422


def test_non_integer_amount_rejected(client):
    resp = post_preview(client, {"customerLevel": "GOLD", "amount": 1200.5})
    assert resp.status_code == 422


@pytest.mark.parametrize("invalid_coupon", ["RANDOM50", "vip100", "VIP200"])
def test_invalid_coupon_value_rejected(client, invalid_coupon):
    resp = post_preview(
        client, {"customerLevel": "GOLD", "amount": 1200, "coupon": invalid_coupon}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Supplementary tests: determinism
# ---------------------------------------------------------------------------


def test_response_is_deterministic_across_repeated_calls(client):
    """Same input must always produce the same output (per requirements doc:
    'computation must be deterministic')."""
    payload = {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
    responses = [post_preview(client, payload).json() for _ in range(5)]
    first = responses[0]
    for other in responses[1:]:
        assert other == first

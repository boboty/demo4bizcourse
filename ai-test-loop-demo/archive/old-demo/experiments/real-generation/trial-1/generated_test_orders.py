"""
针对 POST /api/orders/discount-preview 的黑盒自动化测试。

依据文档：
  - 需求文档：订单优惠预览接口
  - 验收用例文档（案例 1~7）
  - OpenAPI 契约（DiscountPreviewRequest / DiscountPreviewResponse）

被测服务需已在本地运行：http://127.0.0.1:8811

测试仅通过 HTTP 与被测服务交互，不依赖、不假设任何服务端实现细节。
"""

from __future__ import annotations

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8811"
ENDPOINT = "/api/orders/discount-preview"

# OpenAPI 契约中 DiscountPreviewResponse 的必填字段与期望类型
RESPONSE_REQUIRED_FIELDS = {
    "eligible": bool,
    "discount": int,
    "finalAmount": int,
    "membershipDiscount": int,
    "couponDiscount": int,
    "discountSources": list,
    "reason": str,
    "decisionTrace": list,
}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


def post_preview(client: httpx.Client, payload: dict) -> httpx.Response:
    """向被测接口发起一次优惠预览请求。"""
    return client.post(ENDPOINT, json=payload)


def assert_matches_response_schema(body: dict) -> None:
    """校验响应体符合 OpenAPI 契约中 DiscountPreviewResponse 的字段与类型要求。"""
    for field, expected_type in RESPONSE_REQUIRED_FIELDS.items():
        assert field in body, f"响应缺少必填字段: {field}"
        assert isinstance(body[field], expected_type), (
            f"字段 {field} 类型应为 {expected_type.__name__}，实际为 {type(body[field]).__name__}"
        )
    for item in body["discountSources"]:
        assert isinstance(item, str), "discountSources 中的元素应为字符串"
    for item in body["decisionTrace"]:
        assert isinstance(item, str), "decisionTrace 中的元素应为字符串"


def assert_internal_consistency(body: dict, amount: int) -> None:
    """校验响应内部字段之间满足需求文档描述的逻辑关系（与具体优惠规则无关的通用约束）。"""
    # 优惠总额 = 会员优惠 + 优惠券优惠
    assert body["discount"] == body["membershipDiscount"] + body["couponDiscount"], (
        "discount 应等于 membershipDiscount + couponDiscount"
    )
    # 最终金额 = 订单金额 - 优惠总额
    assert body["finalAmount"] == amount - body["discount"], (
        "finalAmount 应等于订单金额减去 discount"
    )
    # 是否产生优惠应与优惠总额是否大于 0 一致
    assert body["eligible"] == (body["discount"] > 0), (
        "eligible 应与 discount > 0 保持一致"
    )
    # 各优惠金额不应为负
    assert body["discount"] >= 0
    assert body["membershipDiscount"] >= 0
    assert body["couponDiscount"] >= 0
    assert body["finalAmount"] >= 0


# ---------------------------------------------------------------------------
# 验收用例文档中的 7 条用例（逐条对应，作为交付证据）
# ---------------------------------------------------------------------------


class TestAcceptanceCases:
    """每个测试方法对应验收用例文档中的一条用例（AC-1 ~ AC-7）。"""

    def test_ac1_gold_1200_no_coupon(self, client):
        """AC-1: GOLD, amount=1200, 不带优惠券 -> 200; membershipDiscount=100; discount=100; finalAmount=1100"""
        resp = post_preview(client, {"customerLevel": "GOLD", "amount": 1200})
        assert resp.status_code == 200
        body = resp.json()
        assert body["membershipDiscount"] == 100
        assert body["discount"] == 100
        assert body["finalAmount"] == 1100
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=1200)

    def test_ac2_gold_1000_no_coupon(self, client):
        """AC-2: GOLD, amount=1000（边界值），不带优惠券 -> 200; membershipDiscount=100"""
        resp = post_preview(client, {"customerLevel": "GOLD", "amount": 1000})
        assert resp.status_code == 200
        body = resp.json()
        assert body["membershipDiscount"] == 100
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=1000)

    def test_ac3_gold_999_no_coupon(self, client):
        """AC-3: GOLD, amount=999（边界值以下），不带优惠券 -> 200; membershipDiscount=0; reason=NO_DISCOUNT"""
        resp = post_preview(client, {"customerLevel": "GOLD", "amount": 999})
        assert resp.status_code == 200
        body = resp.json()
        assert body["membershipDiscount"] == 0
        assert body["reason"] == "NO_DISCOUNT"
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=999)

    def test_ac4_standard_600_vip100(self, client):
        """AC-4: STANDARD, amount=600, coupon=VIP100 -> 200; couponDiscount=100; finalAmount=500"""
        resp = post_preview(
            client, {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["couponDiscount"] == 100
        assert body["finalAmount"] == 500
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=600)

    def test_ac5_gold_1200_vip100_stacks(self, client):
        """AC-5: GOLD, amount=1200, coupon=VIP100 -> 200; membershipDiscount=100;
        couponDiscount=100; discount=200; finalAmount=1000（会员优惠与优惠券叠加）"""
        resp = post_preview(
            client, {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["membershipDiscount"] == 100
        assert body["couponDiscount"] == 100
        assert body["discount"] == 200
        assert body["finalAmount"] == 1000
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=1200)

    def test_ac6_gold_1200_vip100_no_stack(self, client):
        """AC-6: GOLD, amount=1200, coupon=VIP100-NO-STACK -> 200; membershipDiscount=100;
        couponDiscount=0; discount=100; finalAmount=1100（不与会员优惠叠加，保留会员优惠）"""
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
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=1200)

    def test_ac7_invalid_customer_level_rejected(self, client):
        """AC-7: customerLevel=PLATINUM（非法取值）, amount=1200, coupon=VIP100 -> 422"""
        resp = post_preview(
            client,
            {"customerLevel": "PLATINUM", "amount": 1200, "coupon": "VIP100"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 补充测试：直接源自需求文档文字描述的业务规则，作为对验收用例的必要补充
# ---------------------------------------------------------------------------


class TestMembershipRuleBoundaries:
    """需求：'当 customerLevel = GOLD 且 amount >= 1000 时，享受会员优惠 100 元；
    不满足以上条件时，会员优惠为 0 元。' 这里补充验证非 GOLD 等级不享受会员优惠。"""

    @pytest.mark.parametrize("level", ["SILVER", "STANDARD"])
    def test_non_gold_level_never_gets_membership_discount(self, client, level):
        # 使用远高于 1000 的金额，排除金额门槛的干扰，专门验证等级条件
        resp = post_preview(client, {"customerLevel": level, "amount": 5000})
        assert resp.status_code == 200
        body = resp.json()
        assert body["membershipDiscount"] == 0
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=5000)


class TestCouponRuleWithoutMembership:
    """需求：VIP100 / VIP100-NO-STACK 的'不与会员优惠共同生效'规则，
    仅描述了'同时满足会员优惠条件'时的行为（见验收用例 AC-6）。
    此处补充验证：当会员优惠条件本身不满足时，两种优惠券仍各自提供 100 元优惠，
    与需求中'优惠券:VIP100/VIP100-NO-STACK：优惠100元'的基础规则一致。"""

    @pytest.mark.parametrize("coupon", ["VIP100", "VIP100-NO-STACK"])
    def test_coupon_applies_when_membership_condition_not_met(self, client, coupon):
        # STANDARD 等级不满足会员优惠条件（无论金额），单独验证优惠券效果
        resp = post_preview(
            client, {"customerLevel": "STANDARD", "amount": 1200, "coupon": coupon}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["membershipDiscount"] == 0
        assert body["couponDiscount"] == 100
        assert body["discount"] == 100
        assert body["finalAmount"] == 1100
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=1200)


class TestNoDiscountCase:
    """需求：未使用优惠券、且不满足会员优惠条件时，不产生优惠。"""

    def test_no_coupon_no_membership_condition_zero_discount(self, client):
        resp = post_preview(client, {"customerLevel": "STANDARD", "amount": 0})
        assert resp.status_code == 200
        body = resp.json()
        assert body["eligible"] is False
        assert body["discount"] == 0
        assert body["membershipDiscount"] == 0
        assert body["couponDiscount"] == 0
        assert body["finalAmount"] == 0
        assert body["discountSources"] == []
        assert_matches_response_schema(body)
        assert_internal_consistency(body, amount=0)


# ---------------------------------------------------------------------------
# 输入校验测试：依据 OpenAPI 契约中的字段约束（必填、取值范围、枚举）
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_amount_below_minimum_is_rejected(self, client):
        """契约：amount 的 minimum 为 0，负数应被拒绝。"""
        resp = post_preview(client, {"customerLevel": "GOLD", "amount": -1})
        assert resp.status_code == 422

    def test_missing_customer_level_is_rejected(self, client):
        """契约：customerLevel 为必填字段。"""
        resp = post_preview(client, {"amount": 1200})
        assert resp.status_code == 422

    def test_missing_amount_is_rejected(self, client):
        """契约：amount 为必填字段。"""
        resp = post_preview(client, {"customerLevel": "GOLD"})
        assert resp.status_code == 422

    def test_invalid_coupon_value_is_rejected(self, client):
        """契约：coupon 只能是 VIP100 / VIP100-NO-STACK / null 之一。"""
        resp = post_preview(
            client,
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "NOT_A_REAL_COUPON"},
        )
        assert resp.status_code == 422

    def test_omitted_coupon_is_accepted(self, client):
        """coupon 为可选字段，不传应被正常接受（等价于未使用优惠券）。"""
        resp = post_preview(client, {"customerLevel": "SILVER", "amount": 100})
        assert resp.status_code == 200
        body = resp.json()
        assert body["couponDiscount"] == 0

    def test_null_coupon_is_accepted(self, client):
        """契约：coupon 允许显式传 null，等价于未使用优惠券。"""
        resp = post_preview(
            client, {"customerLevel": "GOLD", "amount": 1200, "coupon": None}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["couponDiscount"] == 0
        assert body["membershipDiscount"] == 100


# ---------------------------------------------------------------------------
# 确定性测试：需求文档要求"相同输入永远得到相同输出"
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.parametrize(
        "payload",
        [
            {"customerLevel": "GOLD", "amount": 1200},
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100"},
            {"customerLevel": "GOLD", "amount": 1200, "coupon": "VIP100-NO-STACK"},
            {"customerLevel": "STANDARD", "amount": 600, "coupon": "VIP100"},
        ],
    )
    def test_same_input_yields_identical_response(self, client, payload):
        first = post_preview(client, payload)
        second = post_preview(client, payload)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()

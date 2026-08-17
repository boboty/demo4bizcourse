from app.models import DiscountPreviewRequest, DiscountPreviewResponse


GOLD_THRESHOLD = 1000
GOLD_DISCOUNT = 100
VIP_DISCOUNT = 100


def preview_discount(order: DiscountPreviewRequest) -> DiscountPreviewResponse:
    """以固定规则计算订单优惠，并保留课堂所需的决策证据。"""

    trace: list[str] = ["CHECK_GOLD_LEVEL"]
    membership_discount = 0
    if order.customerLevel == "GOLD" and order.amount >= GOLD_THRESHOLD:
        membership_discount = GOLD_DISCOUNT
        trace.append("APPLY_GOLD_DISCOUNT")
    elif order.customerLevel == "GOLD":
        trace.append("GOLD_THRESHOLD_NOT_MET")

    coupon_discount = 0
    if order.coupon is not None:
        trace.append("CHECK_VIP_COUPON")

    if order.coupon == "VIP100":
        coupon_discount = VIP_DISCOUNT
        trace.append("APPLY_VIP_COUPON")
    elif order.coupon == "VIP100-NO-STACK":
        if membership_discount:
            trace.extend(["VIP_COUPON_NOT_STACKABLE", "RETAIN_GOLD_DISCOUNT"])
        else:
            coupon_discount = VIP_DISCOUNT
            trace.append("APPLY_VIP_COUPON")

    discount = membership_discount + coupon_discount
    sources: list[str] = []
    if membership_discount:
        sources.append("GOLD_MEMBERSHIP")
    if coupon_discount:
        sources.append("VIP_COUPON")

    if membership_discount and coupon_discount:
        reason = "GOLD_LEVEL_AND_VIP_COUPON"
    elif membership_discount:
        reason = "GOLD_MEMBERSHIP_DISCOUNT"
    elif coupon_discount:
        reason = "VIP_COUPON_DISCOUNT"
    else:
        reason = "NO_DISCOUNT"

    return DiscountPreviewResponse(
        eligible=discount > 0,
        discount=discount,
        finalAmount=order.amount - discount,
        membershipDiscount=membership_discount,
        couponDiscount=coupon_discount,
        discountSources=sources,
        reason=reason,
        decisionTrace=trace,
    )


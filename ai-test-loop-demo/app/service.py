from app.models import OrderCalculateRequest, OrderCalculateResponse


DISCOUNT_THRESHOLD = 1000
GOLD_DISCOUNT = 200
SILVER_DISCOUNT = 100


def calculate_order(order: OrderCalculateRequest) -> OrderCalculateResponse:
    """按会员等级与金额门槛计算订单优惠。"""

    discount = 0
    if order.memberLevel == "GOLD" and order.amount >= DISCOUNT_THRESHOLD:
        discount = GOLD_DISCOUNT
    elif order.memberLevel == "SILVER" and order.amount >= DISCOUNT_THRESHOLD:
        discount = SILVER_DISCOUNT

    final_amount = order.amount
    return OrderCalculateResponse(
        status="SUCCESS",
        discount=discount,
        finalAmount=final_amount,
    )

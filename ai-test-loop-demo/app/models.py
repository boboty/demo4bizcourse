from typing import Literal

from pydantic import BaseModel, Field


CustomerLevel = Literal["GOLD", "SILVER", "STANDARD"]
CouponCode = Literal["VIP100", "VIP100-NO-STACK"] | None


class DiscountPreviewRequest(BaseModel):
    customerLevel: CustomerLevel
    amount: int = Field(ge=0)
    coupon: CouponCode = None


class DiscountPreviewResponse(BaseModel):
    eligible: bool
    discount: int
    finalAmount: int
    membershipDiscount: int
    couponDiscount: int
    discountSources: list[str]
    reason: str
    decisionTrace: list[str]


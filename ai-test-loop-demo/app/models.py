from typing import Literal

from pydantic import BaseModel, Field


MemberLevel = Literal["GOLD", "SILVER", "STANDARD"]


class OrderCalculateRequest(BaseModel):
    memberLevel: MemberLevel
    amount: int = Field(ge=0)


class OrderCalculateResponse(BaseModel):
    status: Literal["SUCCESS"] = "SUCCESS"
    discount: int
    finalAmount: int

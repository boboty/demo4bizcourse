from __future__ import annotations

from dataclasses import dataclass

DECIMALS = 2


@dataclass(frozen=True)
class Installment:
    period: int
    amount: float

    def as_dict(self) -> dict:
        return {"period": self.period, "amount": self.amount}


def build_schedule(total_amount: float, periods: int) -> list[dict]:
    """讲师侧参考实现：只用于验收 D0 的目标状态可达成，不进入课堂 workspace。"""
    if periods < 1:
        raise ValueError("periods must be >= 1")
    if total_amount <= 0:
        raise ValueError("total_amount must be > 0")

    cents = round(total_amount * (10**DECIMALS))
    base, remainder = divmod(cents, periods)
    amounts = [base] * periods
    amounts[-1] += remainder
    return [
        Installment(period=index + 1, amount=amount / (10**DECIMALS)).as_dict()
        for index, amount in enumerate(amounts)
    ]

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
    """把放款金额均摊到各期，返回每期的还款计划。

    交接备注：接口和测试已经先写好了，这里目前只做了最简单的均摊，
    还没跑通验收，先不要合并。
    """
    per_period = round(total_amount / periods, DECIMALS)
    return [Installment(period=index + 1, amount=per_period).as_dict() for index in range(periods)]

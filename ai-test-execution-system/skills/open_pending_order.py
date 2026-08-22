"""Skill: open_pending_order。"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from skills.contracts import ExecutionContext, require_step, skill_error
from tools import ui


NAME = "open_pending_order"
PURPOSE = "在已登录 UI 中打开待付款订单。"


def _find_ready(driver: Any, locator: Dict[str, str], timeout_seconds: int = 25) -> Dict[str, str]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            return ui.find_element(driver, locator)
        except Exception as error:
            last_error = error
            time.sleep(0.5)
    raise RuntimeError("未找到元素 {0}：{1}".format(locator, last_error))


def open_pending_order(context: ExecutionContext) -> Dict[str, Any]:
    """输入已登录 context；输出 opened/order_id；失败为 OPEN_PENDING_ORDER_FAILED。"""
    try:
        step = require_step(context.case, NAME)
        element = _find_ready(context.driver, step["locator"])
        ui.click(context.driver, element)
        detail = _find_ready(context.driver, {"using": "css selector", "value": "#order-detail"})
        deadline = time.monotonic() + 25
        actual = ""
        while time.monotonic() < deadline:
            actual = ui.get_text(context.driver, detail)
            if context.order_id and context.order_id in actual and "PENDING_PAY" in actual:
                return {"opened": True, "order_id": context.order_id}
            time.sleep(0.5)
        raise AssertionError("待付款订单详情断言失败：实际 {0!r}".format(actual))
    except Exception as error:
        raise skill_error(NAME, "OPEN_PENDING_ORDER_FAILED", error, {"order_id": context.order_id}) from error

"""Skill: pay_order，只负责 UI 支付交互和页面结果。"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from instructor.observer_events import publish_context_event
from skills.contracts import ExecutionContext, require_step, skill_error
from tools import ui


NAME = "pay_order"
PURPOSE = "点击支付按钮并确认页面显示支付结果；不判定完整业务测试通过。"


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


def pay_order(context: ExecutionContext) -> Dict[str, Any]:
    """输入已打开订单 context；输出 ui_result；失败为 PAY_ORDER_UI_FAILED。"""
    expected_text = ""
    actual = ""
    try:
        step = require_step(context.case, NAME)
        element = _find_ready(context.driver, step["locator"])
        ui.click(context.driver, element)
        assertion = context.case["assertions"]["ui"]
        expected_text = assertion["expected_text"]
        result_element = _find_ready(context.driver, assertion["locator"])
        deadline = time.monotonic() + 25
        actual = ""
        while time.monotonic() < deadline:
            actual = ui.get_text(context.driver, result_element)
            if actual == assertion["expected_text"]:
                context.record["ui_assertion"] = "PASS"
                publish_context_event(
                    context,
                    source="ui",
                    stage=NAME,
                    event="ui_assertion",
                    status="PASS",
                    title="UI Assertion",
                    actual={"ui_result": actual},
                    expected={"ui_result": expected_text},
                    fact_results={"ui_result": "PASS"},
                )
                return {"ui_result": "PASS", "text": actual}
            time.sleep(0.5)
        raise AssertionError(
            "UI 断言失败：期望 {0!r}，实际 {1!r}".format(assertion["expected_text"], actual)
        )
    except Exception as error:
        publish_context_event(
            context,
            source="ui",
            stage=NAME,
            event="ui_assertion",
            status="FAIL",
            title="UI Assertion",
            actual={"ui_result": actual} if actual else None,
            expected={"ui_result": expected_text} if expected_text else None,
            fact_results={"ui_result": "FAIL"} if expected_text else None,
        )
        raise skill_error(NAME, "PAY_ORDER_UI_FAILED", error, {"order_id": context.order_id}) from error

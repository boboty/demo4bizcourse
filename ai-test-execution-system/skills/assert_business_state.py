"""Skill: assert_business_state，独立通过 API 判定业务事实。"""

from __future__ import annotations

from typing import Any, Dict

from skills.contracts import ExecutionContext, assert_expected_facts, skill_error
from tools.api import require_success


NAME = "assert_business_state"
PURPOSE = "通过 API 独立确认订单、支付记录和库存的固定四项事实。"
REQUIRED_FACTS = {
    "order_status": "PAID",
    "payment_count": 1,
    "payment_record.status": "SUCCEEDED",
    "inventory.available_quantity": 9,
}


def assert_business_state(context: ExecutionContext) -> Dict[str, Any]:
    """输入 order_id；输出 facts；失败为 BUSINESS_STATE_ASSERTION_FAILED。"""
    try:
        configured = context.case["assertions"]["api_facts"]["equals"]
        if configured != REQUIRED_FACTS:
            raise AssertionError("固定 API 四项事实被修改或缺失。")
        endpoint = context.case["assertions"]["api_facts"]["endpoint"].format(order_id=context.order_id)
        facts = require_success(context.base_url + endpoint)
        assert_expected_facts(facts, REQUIRED_FACTS, "API 业务事实")
        context.record["api_facts"] = facts
        context.record["api_assertion"] = "PASS"
        return {"api_result": "PASS", "facts": facts}
    except Exception as error:
        raise skill_error(NAME, "BUSINESS_STATE_ASSERTION_FAILED", error, {"order_id": context.order_id}) from error

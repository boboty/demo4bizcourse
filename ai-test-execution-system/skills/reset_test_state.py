"""Skill: reset_test_state / reset_order。"""

from __future__ import annotations

from typing import Any, Dict

from skills.contracts import ExecutionContext, assert_expected_facts, skill_error
from tools.api import require_success


NAME = "reset_test_state"
PURPOSE = "通过 cleanup API 恢复待付款订单、零支付和库存 10 的测试状态。"


def reset_test_state(context: ExecutionContext) -> Dict[str, Any]:
    """输入 cleanup contract；输出 cleanup PASS；失败为 RESET_TEST_STATE_FAILED。"""
    try:
        cleanup = context.case["cleanup"]
        result = require_success(context.base_url + cleanup["endpoint"], method="POST")
        cleanup_order_id = result["order_id"]
        facts = require_success(
            context.base_url + context.case["test_data"]["order_facts_endpoint"].format(order_id=cleanup_order_id)
        )
        assert_expected_facts(facts, cleanup["expected_facts"], "cleanup")
        context.record["cleanup"] = "PASS"
        return {"cleanup": "PASS", "order_id": cleanup_order_id, "facts": facts}
    except Exception as error:
        context.record["cleanup"] = "FAIL"
        raise skill_error(NAME, "RESET_TEST_STATE_FAILED", error, {}) from error


reset_order = reset_test_state

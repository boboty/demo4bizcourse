"""Skill: reset_test_state / reset_order。"""

from __future__ import annotations

from typing import Any, Dict

from instructor.observer_events import publish_context_event
from skills.contracts import ExecutionContext, assert_expected_facts, compare_expected_facts, skill_error
from tools.api import require_success


NAME = "reset_test_state"
PURPOSE = "通过 cleanup API 恢复待付款订单、零支付和库存 10 的测试状态。"


def reset_test_state(context: ExecutionContext) -> Dict[str, Any]:
    """输入 cleanup contract；输出 cleanup PASS；失败为 RESET_TEST_STATE_FAILED。"""
    facts: Dict[str, Any] = {}
    expected = context.case.get("cleanup", {}).get("expected_facts", {})
    try:
        cleanup = context.case["cleanup"]
        result = require_success(context.base_url + cleanup["endpoint"], method="POST")
        cleanup_order_id = result["order_id"]
        facts = require_success(
            context.base_url + context.case["test_data"]["order_facts_endpoint"].format(order_id=cleanup_order_id)
        )
        assert_expected_facts(facts, expected, "cleanup")
        context.record["cleanup"] = "PASS"
        publish_context_event(
            context,
            source="api",
            stage=NAME,
            event="cleanup_completed",
            status="PASS",
            title="Cleanup completed",
            actual=facts,
            expected=expected,
            fact_results=compare_expected_facts(facts, expected),
        )
        return {"cleanup": "PASS", "order_id": cleanup_order_id, "facts": facts}
    except Exception as error:
        context.record["cleanup"] = "FAIL"
        publish_context_event(
            context,
            source="api",
            stage=NAME,
            event="cleanup_completed",
            status="FAIL",
            title="Cleanup failed",
            actual=facts or None,
            expected=expected or None,
            fact_results=compare_expected_facts(facts, expected) if facts else None,
        )
        raise skill_error(NAME, "RESET_TEST_STATE_FAILED", error, {}) from error


reset_order = reset_test_state

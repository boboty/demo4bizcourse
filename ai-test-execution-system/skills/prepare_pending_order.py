"""Skill: prepare_pending_order。"""

from __future__ import annotations

from typing import Any, Dict

from skills.contracts import ExecutionContext, assert_expected_facts, skill_error
from tools.api import require_success


NAME = "prepare_pending_order"
PURPOSE = "准备一笔可支付的待付款订单，并验证其初始业务事实。"


def prepare_pending_order(context: ExecutionContext) -> Dict[str, Any]:
    """输入 base_url；输出 order_id/user；失败为 PREPARE_FAILED + context/evidence。"""
    case = context.case
    try:
        data = require_success(
            context.base_url + case["test_data"]["prepare_pending_order_endpoint"],
            method="POST",
        )
        order_id = data.get(case["test_data"]["order_id_response_field"])
        if not order_id or data.get("order_status") != "PENDING_PAY":
            raise AssertionError("prepare API 未返回 PENDING_PAY order_id。")
        facts_endpoint = case["test_data"]["order_facts_endpoint"].format(order_id=order_id)
        facts = require_success(context.base_url + facts_endpoint)
        assert_expected_facts(
            facts,
            {
                "order_status": "PENDING_PAY",
                "payment_count": 0,
                "inventory.available_quantity": 10,
            },
            "prepare_pending_order 初始事实",
        )
        context.order_id = str(order_id)
        context.user = {"id": data.get("user_id")}
        return {"order_id": context.order_id, "user": context.user, "facts": facts}
    except Exception as error:
        raise skill_error(
            NAME,
            "PREPARE_FAILED",
            error,
            {"endpoint": case.get("test_data", {}).get("prepare_pending_order_endpoint")},
        ) from error

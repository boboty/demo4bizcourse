"""支付超时的业务语义 Retry policy。

这里不是 HTTP 重试器：每一次请求都由 API Tool 单独发送，下一次动作必须先由业务 facts 决策。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from instructor.observer_events import publish_context_event
from skills.assert_business_state import REQUIRED_FACTS
from skills.contracts import ExecutionContext, assert_expected_facts, compare_expected_facts
from skills.prepare_pending_order import prepare_pending_order
from skills.reset_test_state import reset_test_state
from tools.api import HttpResponse, http_request, require_success


PAYMENT_ENDPOINT = "/api/orders/{order_id}/pay"
NOT_COMMITTED_FACTS = {
    "order_status": "PENDING_PAY",
    "payment_count": 0,
    "payment_record": None,
    "inventory.available_quantity": 10,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _facts(base_url: str, order_id: str, case: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = case["assertions"]["api_facts"]["endpoint"].format(order_id=order_id)
    return require_success(base_url + endpoint)


def _attempt(number: int, response: HttpResponse, facts: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "attempt": number,
        "http_status": response.status_code,
        "outcome": "timeout" if response.status_code == 504 else "response",
        "business_facts": facts,
    }


def run_business_retry(
    case: Dict[str, Any],
    base_url: str,
    configuration_override: Dict[str, str],
    artifact_dir: Path,
    observer_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """执行一个 timeout 场景，最多在明确 NOT_COMMITTED 后发起一次 Retry。"""
    artifact_dir.mkdir(parents=True, exist_ok=False)
    record: Dict[str, Any] = {
        "scenario_executor": "business_retry",
        "started_at": utc_now(),
        "result": "FAIL",
        "retry_count": 0,
    }
    history: Dict[str, Any] = {"attempts": [], "decision": None}
    context = ExecutionContext(
        base_url,
        case,
        object(),
        artifact_dir,
        record=record,
        observer=observer_context or {},
    )
    final_facts: Optional[Dict[str, Any]] = None
    timeout_facts: Optional[Dict[str, Any]] = None
    try:
        require_success(base_url + case["preconditions"]["health_endpoint"])
        require_success(base_url + case["test_data"]["reset_endpoint"], method="POST")
        require_success(base_url + "/api/config", method="PUT", payload=configuration_override)
        prepared = prepare_pending_order(context)
        record["order_id"] = prepared["order_id"]

        payment_url = base_url + PAYMENT_ENDPOINT.format(order_id=context.order_id)
        first = http_request(payment_url, method="POST")
        if first.status_code != 504:
            raise AssertionError("timeout 场景第一次付款必须返回 HTTP 504，实际为 {0}".format(first.status_code))
        timeout_facts = _facts(base_url, context.order_id, case)
        history["attempts"].append(_attempt(1, first, timeout_facts))
        publish_context_event(
            context,
            source="retry",
            stage="payment_attempt",
            event="payment_response",
            status="INFO",
            title="HTTP {0}".format(first.status_code),
            actual=timeout_facts,
            evidence=[str(artifact_dir / "api-facts-after-timeout.json")],
        )

        try:
            assert_expected_facts(timeout_facts, NOT_COMMITTED_FACTS, "timeout 后未提交状态")
            decision = "RETRY_ALLOWED"
        except AssertionError:
            assert_expected_facts(timeout_facts, REQUIRED_FACTS, "timeout 后已提交状态")
            decision = "NO_RETRY_ALREADY_COMMITTED"
        history["decision"] = decision
        decision_expected = NOT_COMMITTED_FACTS if decision == "RETRY_ALLOWED" else REQUIRED_FACTS
        publish_context_event(
            context,
            source="retry",
            stage="retry",
            event="retry_decision",
            status="DECISION",
            title="Retry Decision",
            actual=timeout_facts,
            expected=decision_expected,
            fact_results=compare_expected_facts(timeout_facts, decision_expected),
            decision=decision,
            evidence=[str(artifact_dir / "retry_history.json")],
        )

        if decision == "RETRY_ALLOWED":
            # 只有确认 NOT_COMMITTED 后，才清除本次可控 transient fault 并执行唯一一次 Retry。
            require_success(
                base_url + "/api/config",
                method="PUT",
                payload={"payment_mode": "normal"},
            )
            second = http_request(payment_url, method="POST")
            if not second.ok:
                raise AssertionError("获准的唯一 Retry 未成功：HTTP {0}".format(second.status_code))
            final_facts = _facts(base_url, context.order_id, case)
            assert_expected_facts(final_facts, REQUIRED_FACTS, "Retry 后业务事实")
            history["attempts"].append(_attempt(2, second, final_facts))
            publish_context_event(
                context,
                source="retry",
                stage="payment_attempt",
                event="retry_completed",
                status="PASS",
                title="Retry #1",
                actual=final_facts,
                expected=REQUIRED_FACTS,
                fact_results=compare_expected_facts(final_facts, REQUIRED_FACTS),
            )
            record["retry_count"] = 1
        else:
            final_facts = timeout_facts
            record["retry_count"] = 0
            # 已提交时不再发第二次支付请求，Payment 数量保持为 1。
            assert_expected_facts(final_facts, REQUIRED_FACTS, "已提交且禁止 Retry 的业务事实")
            publish_context_event(
                context,
                source="retry",
                stage="payment_attempt",
                event="retry_completed",
                status="PASS",
                title="No Retry",
                actual=final_facts,
                expected=REQUIRED_FACTS,
                fact_results=compare_expected_facts(final_facts, REQUIRED_FACTS),
            )

        record["api_facts"] = final_facts
        record["result"] = "PASS"
    except Exception as error:
        record["error"] = str(error)
        if timeout_facts is not None:
            record["api_facts_after_timeout"] = timeout_facts
    finally:
        try:
            reset_test_state(context)
        except Exception as error:
            record["cleanup"] = "FAIL"
            record["cleanup_error"] = str(error)
            record["result"] = "FAIL"
        else:
            record["cleanup"] = "PASS"
        publish_context_event(
            context,
            source="system",
            stage="scenario",
            event="scenario_completed",
            status="PASS" if record.get("result") == "PASS" else "FAIL",
            title="Scenario completed",
            actual=record.get("api_facts") or record.get("api_facts_after_timeout"),
            expected=REQUIRED_FACTS if record.get("api_facts") else None,
            decision=history.get("decision"),
            evidence=[str(artifact_dir)],
        )
        record["finished_at"] = utc_now()
        (artifact_dir / "retry_history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if timeout_facts is not None:
            (artifact_dir / "api-facts-after-timeout.json").write_text(
                json.dumps(timeout_facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        if final_facts is not None:
            (artifact_dir / "api-facts.json").write_text(
                json.dumps(final_facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        (artifact_dir / "result.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return record

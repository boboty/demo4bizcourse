"""Round 5 确定性 Failure Cause 分类器。

分类只读取结构化执行证据，不读取 scenario_id、文件名或 fault mode 名称。
Failure Cause 与 Stability 是两个独立维度；本模块只负责 Failure Cause。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


CATEGORIES = ("PRODUCT", "ENVIRONMENT", "DEVICE", "AUTOMATION")
UNCLASSIFIED = "UNCLASSIFIED"


def _get(value: Any, dotted_path: str) -> Any:
    current = value
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _mismatches(actual: Dict[str, Any], expected: Dict[str, Any]) -> List[Dict[str, Any]]:
    mismatches = []
    for dotted_path, wanted in expected.items():
        got = _get(actual, dotted_path)
        if got != wanted:
            mismatches.append({"field": dotted_path, "expected": wanted, "actual": got})
    return mismatches


def _result(category: str, reason: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    excluded = {"scenario_id", "case_id", "fault_mode", "filename", "task_path"}
    stable_evidence = {key: value for key, value in evidence.items() if key not in excluded}
    return {"category": category, "reason": reason, "evidence": stable_evidence}


def classify_failure(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """根据结构化 evidence 返回一个稳定的 Failure Cause 结果。

    规则顺序是：服务不可用、设备不可用、业务事实不符、自动化阶段失败，
    其余情况显式返回 UNCLASSIFIED。错误文本本身不会触发分类。
    """

    if not isinstance(evidence, dict):
        return _result(UNCLASSIFIED, "结构化 evidence 不足。", {})

    service_reachable = evidence.get("service_reachable")
    app_reachable = evidence.get("app_reachable")
    failure_stage = evidence.get("failure_stage")

    if service_reachable is False or app_reachable is False:
        if failure_stage in {"health", "preflight", "service_availability"}:
            return _result(\
                "ENVIRONMENT",
                "服务可用性检查失败，尚未进入业务 Workflow。",
                evidence,
            )

    if (
        service_reachable is True
        and evidence.get("device_preflight") is False
        and failure_stage in {"device_preflight", "device_health"}
    ) or (
        service_reachable is True
        and evidence.get("device_preflight") is True
        and evidence.get("session_created") is False
        and failure_stage == "create_session"
    ):
        return _result("DEVICE", "服务可用，但设备健康检查或会话建立失败。", evidence)

    actual_facts = evidence.get("actual_facts")
    expected_facts = evidence.get("expected_facts")
    if (
        evidence.get("failure_skill") == "assert_business_state"
        and evidence.get("ui_assertion") == "PASS"
        and isinstance(actual_facts, dict)
        and isinstance(expected_facts, dict)
    ):
        mismatches = _mismatches(actual_facts, expected_facts)
        if mismatches:
            classified_evidence = dict(evidence)
            classified_evidence["mismatches"] = mismatches
            return _result(
                "PRODUCT",
                "UI 交互完成，但业务事实违反固定 assertion。",
                classified_evidence,
            )

    automation_stages: Iterable[str] = {
        "locator",
        "wait",
        "script",
        "login",
        "open_pending_order",
        "pay_order",
    }
    if (
        service_reachable is True
        and app_reachable is True
        and evidence.get("device_preflight") is True
        and evidence.get("session_created") is True
        and evidence.get("page_reached") is True
        and evidence.get("workflow_started") is True
        and evidence.get("payment_executed") is False
        and failure_stage in automation_stages
    ):
        return _result("AUTOMATION", "设备与页面可用，但 UI 自动化阶段失败。", evidence)

    return _result(UNCLASSIFIED, "现有结构化 evidence 不足以确定 Failure Cause。", evidence)

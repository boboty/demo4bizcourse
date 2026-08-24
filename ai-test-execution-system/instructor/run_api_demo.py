#!/usr/bin/env python
"""API-only classroom entry point for the Demo 2 payment scenarios.

The wrapper only composes the existing API Tool, Skills, and business Retry
policy.  It does not send HTTP requests on behalf of an Agent or define new
payment rules.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner.retry_policy import PAYMENT_ENDPOINT, run_business_retry
from scripts.run_pay_order_ios import read_case
from skills.assert_business_state import assert_business_state
from skills.contracts import ExecutionContext
from skills.prepare_pending_order import prepare_pending_order
from skills.reset_test_state import reset_test_state
from tools.api import http_request, require_success
from instructor.observer_events import publish_event


SCENARIOS = ("normal", "timeout-before", "timeout-after")
API_ARTIFACT_ROOT = ROOT / "artifacts" / "runs" / "api-demo"


def utc_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return "{0}-{1}".format(timestamp, uuid.uuid4().hex[:8])


def scenario_artifact_dir(
    scenario: str, artifact_root: Optional[Path] = None
) -> Path:
    root = artifact_root or API_ARTIFACT_ROOT
    run_dir = root / utc_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir / scenario


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_normal(case: Dict[str, Any], base_url: str, artifact_dir: Path) -> Dict[str, Any]:
    """Run reset → config → prepare → pay → facts → cleanup once."""
    artifact_dir.mkdir(parents=True, exist_ok=False)
    record: Dict[str, Any] = {
        "scenario": "normal",
        "executor": "api_demo_wrapper",
        "result": "FAIL",
        "artifact_policy": "ignore: runtime classroom evidence",
    }
    observer = {
        "demo": "demo2",
        "run_id": artifact_dir.parent.name,
        "scenario_id": "normal",
    }
    context = ExecutionContext(base_url, case, object(), artifact_dir, record=record, observer=observer)
    publish_event(
        source="system",
        demo="demo2",
        run_id=observer["run_id"],
        scenario_id="normal",
        stage="scenario",
        event="scenario_started",
        status="RUNNING",
        title="Normal payment started",
    )
    try:
        require_success(base_url + case["preconditions"]["health_endpoint"])
        require_success(base_url + case["test_data"]["reset_endpoint"], method="POST")
        require_success(
            base_url + "/api/config",
            method="PUT",
            payload=case["configuration"],
        )
        prepare_pending_order(context)
        payment_url = base_url + PAYMENT_ENDPOINT.format(order_id=context.order_id)
        payment = http_request(payment_url, method="POST")
        record["payment_http_status"] = payment.status_code
        publish_event(
            source="api",
            demo="demo2",
            run_id=observer["run_id"],
            scenario_id="normal",
            stage="pay",
            event="payment_response",
            status="PASS" if payment.ok else "FAIL",
            title="POST /pay",
            facts={"http_status": payment.status_code},
        )
        if not payment.ok:
            raise AssertionError("normal 场景支付请求失败：HTTP {0}".format(payment.status_code))
        facts = assert_business_state(context)["facts"]
        record["api_facts"] = facts
        record["facts_assertion"] = "PASS"
        record["result"] = "PASS"
    except Exception as error:
        record["error"] = str(error)
    finally:
        try:
            reset_test_state(context)
        except Exception as error:
            record["cleanup"] = "FAIL"
            record["cleanup_error"] = str(error)
            record["result"] = "FAIL"
        else:
            record["cleanup"] = "PASS"
        publish_event(
            source="system",
            demo="demo2",
            run_id=observer["run_id"],
            scenario_id="normal",
            stage="scenario",
            event="scenario_completed",
            status="PASS" if record.get("result") == "PASS" else "FAIL",
            title="Normal payment completed",
            actual=record.get("api_facts"),
            expected=case.get("assertions", {}).get("api_facts", {}).get("equals"),
            evidence=[str(artifact_dir)],
            update_current=False,
        )
        write_json(artifact_dir / "result.json", record)
    return record


def run_timeout(
    scenario: str, case: Dict[str, Any], base_url: str, artifact_dir: Path
) -> Dict[str, Any]:
    mode = "timeout_before_commit" if scenario == "timeout-before" else "timeout_after_commit"
    configuration = dict(case["configuration"])
    configuration["payment_mode"] = mode
    observer_context = {
        "demo": "demo2",
        "run_id": artifact_dir.parent.name,
        "scenario_id": scenario,
    }
    result = run_business_retry(
        case, base_url, configuration, artifact_dir, observer_context=observer_context
    )
    history_path = artifact_dir / "retry_history.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.is_file() else {}
    publish_event(
        source="system",
        demo="demo2",
        run_id=artifact_dir.parent.name,
        scenario_id=scenario,
        stage="scenario",
        event="scenario_completed",
        status="PASS" if result.get("result") == "PASS" else "FAIL",
        title="{0} completed".format(scenario),
        actual=result.get("api_facts"),
        expected=case.get("assertions", {}).get("api_facts", {}).get("equals"),
        decision=history.get("decision"),
        evidence=[str(artifact_dir)],
        update_current=False,
    )
    return result


def print_normal_result(result: Dict[str, Any], artifact_dir: Path) -> None:
    print("normal")
    print("HTTP {0}".format(result.get("payment_http_status", "ERROR")))
    print("GET facts: {0}".format(result.get("facts_assertion", "FAIL")))
    print("cleanup: {0}".format(result.get("cleanup", "FAIL")))
    print("artifact: {0}".format(artifact_dir))


def print_timeout_result(
    scenario: str, result: Dict[str, Any], artifact_dir: Path
) -> None:
    history = json.loads((artifact_dir / "retry_history.json").read_text(encoding="utf-8"))
    decision = history.get("decision")
    timeout_facts = history["attempts"][0].get("business_facts", {})
    committed = decision == "NO_RETRY_ALREADY_COMMITTED"
    print(scenario)
    print("HTTP {0}".format(history["attempts"][0]["http_status"]))
    print("业务 facts {0}".format("已提交" if committed else "未提交"))
    print(decision)
    if committed:
        print("不发送第二次支付请求")
    else:
        print("只 Retry 一次")
    print("最终 facts: {0}".format("PASS" if result.get("result") == "PASS" else "FAIL"))
    print("artifact: {0}".format(artifact_dir))
    if not timeout_facts:
        print("warning: timeout facts 缺失")


def run_scenario(
    scenario: str,
    case: Dict[str, Any],
    base_url: str,
    artifact_root: Optional[Path] = None,
) -> Dict[str, Any]:
    artifact_dir = scenario_artifact_dir(scenario, artifact_root)
    if scenario == "normal":
        result = run_normal(case, base_url, artifact_dir)
        print_normal_result(result, artifact_dir)
    else:
        result = run_timeout(scenario, case, base_url, artifact_dir)
        print_timeout_result(scenario, result, artifact_dir)
    return result


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        choices=(*SCENARIOS, "all"),
        help="课堂 API 场景；all 按 normal、timeout-before、timeout-after 顺序执行",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEMO_BASE_URL", "http://127.0.0.1:8000"),
        help="FastAPI 地址，默认读取 DEMO_BASE_URL 或 localhost:8000",
    )
    args = parser.parse_args(argv)
    case = read_case(ROOT / "cases" / "pay_order.yaml")
    scenarios = SCENARIOS if args.scenario == "all" else (args.scenario,)
    results = []
    for scenario in scenarios:
        results.append(run_scenario(scenario, case, args.base_url.rstrip("/")))
    return 0 if all(result.get("result") == "PASS" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

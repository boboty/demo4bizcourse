"""受控 timing/wait 实验：同一个支付任务产生真实混合 PASS/FAIL。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import create_app  # noqa: E402
from app.runtime import RuntimeStore  # noqa: E402
from runner.failure_classifier import classify_failure  # noqa: E402
from runner.stability import append_history, summarize_history  # noqa: E402


CASE_ID = "flaky_automation"
WAIT_TIMEOUT_SECONDS = 0.02
# 这是元素出现延迟 profile，不是预生成的结果；最终结果由实际 wait 条件决定。
CONTROLLED_DELAY_PROFILE = (0.004, 0.040, 0.005, 0.050, 0.006, 0.045, 0.004, 0.050, 0.006, 0.040, 0.005, 0.045)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wait_for_element_after_delay(delay_seconds: float, timeout_seconds: float) -> Dict[str, Any]:
    """等待实际元素 ready 时间；超时结果由时钟判断，不直接指定 PASS/FAIL。"""
    started = time.monotonic()
    ready_at = started + delay_seconds
    deadline = started + timeout_seconds
    while time.monotonic() < deadline:
        if time.monotonic() >= ready_at:
            return {"found": True, "wait_seconds": round(time.monotonic() - started, 6)}
        time.sleep(0.001)
    return {"found": False, "wait_seconds": round(time.monotonic() - started, 6)}


def run_flaky_experiment(
    output_root: Path,
    history_path: Path,
    runs: int = len(CONTROLLED_DELAY_PROFILE),
) -> Dict[str, Any]:
    if runs != len(CONTROLLED_DELAY_PROFILE):
        raise ValueError("课堂实验固定执行 12 次，以保证使用同一 timing profile。")
    output_root.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        history_path.unlink()

    records: List[Dict[str, Any]] = []
    for index, delay_seconds in enumerate(CONTROLLED_DELAY_PROFILE, start=1):
        started = time.monotonic()
        client = TestClient(create_app(RuntimeStore(output_root / "runtime-state.json")))
        assert client.post("/api/reset").status_code == 200
        prepared = client.post("/api/test-data/prepare-pending-order")
        order_id = prepared.json()["order_id"]
        page = client.get("/")
        page_reached = page.status_code == 200 and 'id="pay-now"' in page.text
        wait_result = wait_for_element_after_delay(delay_seconds, WAIT_TIMEOUT_SECONDS)
        payment_executed = False
        result = "FAIL"
        failure_category = None
        evidence: Dict[str, Any] = {
            "service_reachable": True,
            "app_reachable": page_reached,
            "device_preflight": True,
            "session_created": True,
            "page_reached": page_reached,
            "workflow_started": True,
            "payment_executed": False,
            "failure_stage": "wait",
            "wait": wait_result,
        }
        if wait_result["found"]:
            paid = client.post("/api/orders/{0}/pay".format(order_id))
            payment_executed = paid.status_code == 200
            facts = client.get("/api/orders/{0}/facts".format(order_id)).json()
            result = "PASS" if payment_executed and facts["inventory"]["available_quantity"] == 9 else "FAIL"
        else:
            facts = client.get("/api/orders/{0}/facts".format(order_id)).json()
        evidence["payment_executed"] = payment_executed
        evidence["actual_facts"] = facts
        if result == "FAIL":
            evidence["failure_skill"] = "pay_order"
            classifier = classify_failure(evidence)
            failure_category = classifier["category"]
        record = {
            "run_id": "flaky-{0:03d}".format(index),
            "timestamp": utc_now(),
            "case_id": CASE_ID,
            "result": result,
            "failure_category": failure_category,
            "duration": round(time.monotonic() - started, 6),
            "timing": {"configured_delay_seconds": delay_seconds, "timeout_seconds": WAIT_TIMEOUT_SECONDS},
        }
        append_history(history_path, record)
        _write_json(output_root / "runs" / "run-{0:03d}.json".format(index), {"result": record, "evidence": evidence})
        records.append(record)

    stability = summarize_history(history_path)
    summary = {
        "case_id": CASE_ID,
        "total_runs": len(records),
        "pass_count": sum(item["result"] == "PASS" for item in records),
        "fail_count": sum(item["result"] == "FAIL" for item in records),
        "failure_category": "AUTOMATION",
        "stability": stability["stability"],
        "history": "artifacts/history/flaky_automation.jsonl",
        "runs": records,
    }
    _write_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "artifacts" / "round5" / "flaky-automation")
    parser.add_argument("--history", type=Path, default=ROOT / "artifacts" / "history" / "flaky_automation.jsonl")
    args = parser.parse_args()
    summary = run_flaky_experiment(args.output_root.resolve(), args.history.resolve())
    print(json.dumps({key: summary[key] for key in ("total_runs", "pass_count", "fail_count", "failure_category", "stability")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

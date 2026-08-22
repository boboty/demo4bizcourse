"""Run Plan CLI：只支持显式 --run-now 的 serial 执行。"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from runner.report import build_report
from runner.suite_runner import load_suite, run_suite
from scripts.run_pay_order_ios import check_prerequisites, lan_ip, read_case, require_ok


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def load_plan(path: Path) -> Dict[str, Any]:
    plan = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {"version", "plan_id", "suite", "execution_mode", "preflight", "artifact_root", "report_output"}
    if not required.issubset(plan):
        raise ValueError("Run Plan 缺少必填字段：{0}".format(sorted(required - set(plan))))
    if plan["version"] != 1:
        raise ValueError("Run Plan 只支持 version: 1。")
    if plan["execution_mode"] != "serial":
        raise ValueError("Round 4 Run Plan 只支持 execution_mode: serial。")
    if plan["preflight"].get("require_physical_device") is not True:
        raise ValueError("Round 4 Run Plan 必须声明 require_physical_device: true。")
    return plan


def run_now(plan_path: Path, base_url: Optional[str] = None) -> Dict[str, Any]:
    project_root = plan_path.parent.parent
    plan = load_plan(plan_path)
    suite_path = (project_root / plan["suite"]).resolve()
    suite = load_suite(suite_path)
    first_task = (project_root / suite["scenarios"][0]["task"]).resolve()
    case = read_case(first_task)
    base_url = (base_url or "http://{0}:8000".format(lan_ip())).rstrip("/")
    require_ok(base_url + plan["preflight"]["health_endpoint"], timeout=10)
    check_prerequisites(case)

    run_id = utc_run_id()
    run_dir = (project_root / plan["artifact_root"] / run_id).resolve()
    run_record = run_suite(suite_path, run_dir, base_url=base_url)
    report_path = (project_root / plan["report_output"] / run_id / "report.md").resolve()
    report = build_report(run_dir, report_path)
    output = {"plan_id": plan["plan_id"], "run": run_record, "report": report, "report_path": str(report_path)}
    (run_dir / "run-plan.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-now", type=Path, required=True, help="显式立即执行一个 serial Run Plan")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()
    result = run_now(args.run_now.resolve(), args.base_url)
    return 0 if result["run"]["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

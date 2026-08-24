#!/usr/bin/env python3
"""定位最近一个包含完整 Round 4 运行证据的 artifacts run。"""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any, Dict


def _read_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON 顶层必须是 object：{0}".format(path))
    return value


def is_complete_run(run_dir: Path, reports_root: Path) -> bool:
    run_path = run_dir / "run.json"
    plan_path = run_dir / "run-plan.json"
    report_path = reports_root / run_dir.name / "report.md"
    if not run_dir.is_dir() or not run_path.is_file() or not plan_path.is_file() or not report_path.is_file():
        return False
    try:
        run = _read_json(run_path)
        plan = _read_json(plan_path)
        scenarios = run.get("scenarios")
        planned_run = plan.get("run")
        if run.get("run_id") != run_dir.name or not isinstance(scenarios, list) or not scenarios:
            return False
        if not isinstance(planned_run, dict) or planned_run.get("run_id") != run_dir.name:
            return False
        for scenario in scenarios:
            scenario_id = scenario.get("scenario_id") if isinstance(scenario, dict) else None
            result_path = run_dir / "cases" / str(scenario_id) / "result.json"
            if not scenario_id or not result_path.is_file():
                return False
            _read_json(result_path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return True


def find_latest_complete_run(project_root: Path) -> Path:
    artifacts_root = project_root / "artifacts" / "runs"
    reports_root = project_root / "reports"
    candidates = sorted((item for item in artifacts_root.iterdir() if item.is_dir()), reverse=True)
    for run_dir in candidates:
        if is_complete_run(run_dir, reports_root):
            return run_dir.resolve()
    raise FileNotFoundError("没有找到包含完整 run.json、run-plan.json、scenario results 和 report.md 的 Run。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--shell", action="store_true", help="输出可由当前 shell eval 的 RUN_* 变量。")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    run_dir = find_latest_complete_run(project_root)
    run_id = run_dir.name
    report_path = project_root / "reports" / run_id / "report.md"
    if args.as_json:
        print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "report_path": str(report_path)}, ensure_ascii=False))
    elif args.shell:
        print("RUN_DIR={0}".format(shlex.quote(str(run_dir))))
        print("RUN_ID={0}".format(shlex.quote(run_id)))
        print("REPORT_PATH={0}".format(shlex.quote(str(report_path))))
    else:
        print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

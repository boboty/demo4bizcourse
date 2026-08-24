#!/usr/bin/env python3
"""课堂用 Round 4 wrapper：执行正式 Run Plan，但只输出安全的课堂 Gate。"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runner.run_plan import run_now
from scripts.find_latest_complete_run import is_complete_run


def _run_plan() -> Path:
    return ROOT / "schedules" / "nightly.yaml"


def _execute(base_url: Optional[str]) -> tuple[dict, Path]:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        result = run_now(_run_plan(), base_url=base_url)

    run = result.get("run") if isinstance(result, dict) else None
    run_id = run.get("run_id") if isinstance(run, dict) else None
    if not run_id:
        raise RuntimeError("Run Plan 未返回 run_id。")

    run_dir = (ROOT / "artifacts" / "runs" / str(run_id)).resolve()
    reports_root = (ROOT / "reports").resolve()
    if not is_complete_run(run_dir, reports_root):
        raise RuntimeError("本轮 Run artifact 或 report 不完整。")
    return run, run_dir


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=None, help="可选 FastAPI base URL；默认使用现有 runtime 解析。")
    args = parser.parse_args(argv)

    try:
        run, run_dir = _execute(args.base_url)
    except Exception as error:
        print("Demo 4 Test Run", file=sys.stderr)
        print("Run Plan: FAILED", file=sys.stderr)
        print("原因：{0}".format(error), file=sys.stderr)
        return 1

    scenarios = run.get("scenarios", [])
    print("Demo 4 Test Run")
    print("------------------------------")
    print("Run Plan: COMPLETED")
    print("Run ID: {0}".format(run_dir.name))
    print("Execution Mode: {0}".format(run.get("execution_mode", "serial")))
    print("Scenarios: {0}".format(len(scenarios)))
    print("Artifacts: READY")
    print("Report: READY")
    print("Ready for Agent Analysis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

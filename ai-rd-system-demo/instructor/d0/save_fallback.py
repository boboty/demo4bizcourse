#!/usr/bin/env python3
"""保存一次成功跑通的 D0 现场证据，供课堂超时或环境异常时回放。"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()

    result_path = args.source / "result.json"
    if not result_path.is_file():
        raise SystemExit(f"缺少 {result_path}，请先运行 ./scripts/d0_run.sh")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("run_status") != "COMPLETED":
        raise SystemExit(f"最近一次运行状态为 {result.get('run_status')}，不能保存 fallback")
    if result.get("final_test_passed") is not True:
        raise SystemExit("最近一次运行没有走到 PASS，不能保存 fallback")
    if result.get("tests_modified"):
        raise SystemExit("最近一次运行修改了测试文件，不能保存 fallback")
    if not result.get("agent_ran_pytest"):
        raise SystemExit("最近一次运行没有运行 pytest，不能保存 fallback")

    if args.destination.exists():
        shutil.rmtree(args.destination)
    shutil.copytree(args.source, args.destination)
    snapshot = {
        "kind": "SAVED_EVIDENCE",
        "source": str(args.source),
        "baseline_digest": result.get("baseline_digest"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "agent": result.get("agent"),
        "note": "同一个 D0 baseline、同一个任务下真实跑通的一次运行；不是另一个项目的录像。",
    }
    (args.destination / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved D0 fallback evidence: {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""保存一次成功跑通的 D1 工程现场接力证据，供课堂超时或环境异常时回放。"""
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
        raise SystemExit(f"缺少 {result_path}，请先运行 ./scripts/d1_handoff_run.sh")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("run_status") != "COMPLETED":
        raise SystemExit(f"最近一次运行状态为 {result.get('run_status')}，不能保存 fallback")
    if result.get("final_test_passed") is not True:
        raise SystemExit("最近一次运行没有走到测试全绿，不能保存 fallback")
    predictions = result.get("predictions", {})
    if predictions.get("hits") != predictions.get("total"):
        raise SystemExit(f"最近一次运行五项预测只命中 {predictions.get('hits')}/{predictions.get('total')}，不保存为 fallback（可用于课堂讨论，但不是稳定回放素材）")
    if not all(result.get("state_written_back", {}).values()):
        raise SystemExit("最近一次运行没有把状态写回 PROGRESS.md/DECISIONS.md，不能保存 fallback")
    if not result.get("stayed_in_workspace"):
        raise SystemExit("最近一次运行有越界引用其他 workspace/instructor 资产，不能保存 fallback")

    if args.destination.exists():
        shutil.rmtree(args.destination)
    shutil.copytree(args.source, args.destination)
    snapshot = {
        "kind": "SAVED_EVIDENCE",
        "source": str(args.source),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "predictions_hit": f"{predictions.get('hits')}/{predictions.get('total')}",
        "note": "同一个 d1-handoff checkpoint、同一句接手指令下真实跑通的一次运行；不是另一个项目的录像。",
    }
    (args.destination / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved D1 handoff fallback evidence: {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

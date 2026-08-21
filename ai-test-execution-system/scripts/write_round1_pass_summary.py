#!/usr/bin/env python3
"""把已完成的五次真实 Round 1 原始结果整理为可提交的脱敏摘要。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path, help="run_pay_order_ios.py 生成的 batch.json")
    args = parser.parse_args()
    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    runs = batch.get("runs", [])
    if len(runs) != 5 or not batch.get("all_pass") or any(run.get("result") != "PASS" for run in runs):
        raise SystemExit("只能为恰好五次、全部 PASS 的真实执行生成 Round 1 PASS 摘要。")
    lines = [
        "# Round 1 PASS 摘要（脱敏）",
        "",
        "- case: `pay_order`",
        "- execution target: physical iPhone + Mobile Safari + Appium/XCUITest",
        "- UI version: v1",
        "- payment mode: normal",
        "- product bug mode: off",
    ]
    lines.extend("- Run {0}: PASS（UI、API facts、cleanup）".format(run["run"]) for run in runs)
    lines.extend(
        [
            "",
            "原始截图、Appium/设备日志、会话信息与本机路径仅保留在被忽略的 `evidence/round1-*` 中，不提交。",
        ]
    )
    output = ROOT / "evidence" / "round1-pass-summary.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

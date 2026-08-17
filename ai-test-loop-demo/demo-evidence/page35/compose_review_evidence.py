"""组装"独立验收驳回过程"证据文本——不是只截 REJECTED 一行，而是把判据本身拼进同一帧：
命令 + 终端输出 + acceptance.md 里 AC-004 那一行定义的证据要求 + 报告自带的"未重跑pytest"说明。
所有内容都来自真实文件/真实命令输出，没有手写编造的文本。
"""

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    reset = subprocess.run(
        [sys.executable, "scripts/reset_demo.py"], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    gen = subprocess.run(
        [sys.executable, "scripts/run_generated_tests.py"], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    review = subprocess.run(
        [sys.executable, "scripts/run_independent_review.py"], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    report = (PROJECT_ROOT / "evidence" / "independent-review-report.md").read_text(encoding="utf-8")
    acceptance = (PROJECT_ROOT / "business" / "acceptance.md").read_text(encoding="utf-8")
    ac004_row = next(line for line in acceptance.splitlines() if line.startswith("| AC-004"))
    trailer = [line for line in report.splitlines() if "没有重新运行" in line][0]

    lines = []
    lines.append("$ python scripts/run_independent_review.py")
    lines.append("")
    lines.extend(review.stdout.strip("\n").split("\n"))
    lines.append("")
    lines.append("# 判据来自 business/acceptance.md 的 AC-004 定义：")
    lines.append(ac004_row)
    lines.append("")
    lines.append("# 该脚本判定依据（evidence/independent-review-report.md 原文最后一行）：")
    lines.append(trailer)
    text = "\n".join(lines)

    out = PROJECT_ROOT / "demo-evidence" / "page35" / "independent-review-rejection.txt"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

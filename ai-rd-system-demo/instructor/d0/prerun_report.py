#!/usr/bin/env python3
"""把 D0 预跑结果汇总成课堂可用的稳定性报告。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRERUNS = ROOT / "instructor/d0/preruns"
COLUMNS = ("run", "status", "seconds", "loop", "read_first", "saw_fail", "green_after_edit", "tests_modified", "final")


def main() -> int:
    runs = sorted(path for path in PRERUNS.glob("run-*") if (path / "result.json").is_file())
    if not runs:
        raise SystemExit("没有预跑结果，请先运行 ./scripts/d0_prerun.sh")

    rows = []
    for run in runs:
        data = json.loads((run / "result.json").read_text(encoding="utf-8"))
        loop = data.get("loop", {})
        rows.append(
            {
                "run": run.name,
                "status": data.get("run_status"),
                "seconds": data.get("elapsed_seconds"),
                "loop": " → ".join(loop.get("actions", [])),
                "read_first": loop.get("read_or_search_before_edit"),
                "saw_fail": loop.get("observed_failure_before_edit"),
                "green_after_edit": loop.get("green_test_run_after_edit"),
                "tests_modified": data.get("tests_modified"),
                "final": data.get("final_test_summary"),
            }
        )

    good = [row for row in rows if row["status"] == "COMPLETED" and row["saw_fail"] and row["green_after_edit"] and not row["tests_modified"] and row["read_first"]]
    times = [row["seconds"] for row in rows if isinstance(row["seconds"], (int, float))]

    lines = [
        "# D0 预跑稳定性报告",
        "",
        f"- 预跑次数：{len(rows)}",
        f"- 完整链路（先读项目 → 看到真实失败 → 修改 → 复跑转绿）：{len(good)}/{len(rows)}",
        f"- 单次耗时：min {min(times):.1f}s / max {max(times):.1f}s / avg {sum(times) / len(times):.1f}s" if times else "- 单次耗时：无数据",
        "",
        "| run | 状态 | 耗时(s) | 实际链路 | 先读项目 | 看到失败 | 改后转绿 | 改动测试 | 最终测试 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {status} | {seconds} | {loop} | {read_first} | {saw_fail} | {green_after_edit} | {tests_modified} | {final} |".format(**row)
        )
    lines.append("")
    report = ROOT / "instructor/d0/PRERUN-REPORT.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if len(good) == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

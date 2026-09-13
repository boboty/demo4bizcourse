#!/usr/bin/env python3
"""把 D1 工程现场接力预跑结果汇总成课堂稳定性报告。

不做一刀切 PASS/FAIL：五个预测分别统计命中率，供课堂讨论"没命中的项说明
工程现场还缺什么"。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRERUNS = ROOT / "instructor/d1/handoff/preruns"
PREDICTION_KEYS = (
    "1_identified_task",
    "2_identified_done",
    "3_identified_next_step",
    "4_identified_decision",
    "5_correct_verify_command",
)
PREDICTION_LABELS = {
    "1_identified_task": "识别当前任务",
    "2_identified_done": "识别已完成项",
    "3_identified_next_step": "识别下一步",
    "4_identified_decision": "识别一个关键决策",
    "5_correct_verify_command": "使用正确验证命令",
}


def main() -> int:
    runs = sorted(path for path in PRERUNS.glob("run-*") if (path / "result.json").is_file())
    if not runs:
        raise SystemExit("没有预跑结果，请先运行 ./scripts/d1_handoff_prerun.sh")

    rows = []
    for run in runs:
        data = json.loads((run / "result.json").read_text(encoding="utf-8"))
        predictions = data.get("predictions", {})
        rows.append(
            {
                "run": run.name,
                "status": data.get("run_status"),
                "seconds": data.get("elapsed_seconds"),
                "hits": f"{predictions.get('hits')}/{predictions.get('total')}",
                "per_prediction": {key: predictions.get(key, {}).get("hit") for key in PREDICTION_KEYS},
                "health_check_first": data.get("health_check_timing", {}).get("ran_verify_or_pytest_before_first_edit"),
                "final_test_passed": data.get("final_test_passed"),
                "state_written_back": all(data.get("state_written_back", {}).values()),
                "stayed_in_workspace": data.get("stayed_in_workspace"),
            }
        )

    times = [row["seconds"] for row in rows if isinstance(row["seconds"], (int, float))]
    completed = [row for row in rows if row["status"] == "COMPLETED"]

    lines = [
        "# D1 工程现场接力｜预跑稳定性报告",
        "",
        f"- 预跑次数：{len(rows)}",
        f"- COMPLETED（未超时/未报错）：{len(completed)}/{len(rows)}",
        f"- 单次耗时：min {min(times):.1f}s / max {max(times):.1f}s / avg {sum(times) / len(times):.1f}s" if times else "- 单次耗时：无数据",
        "",
        "## 五项预测命中率（分别统计，不做一刀切）",
        "",
    ]
    for key in PREDICTION_KEYS:
        hit_count = sum(1 for row in rows if row["per_prediction"].get(key))
        lines.append(f"- {PREDICTION_LABELS[key]}：{hit_count}/{len(rows)}")

    lines += [
        "",
        "## 逐次明细",
        "",
        "| run | 状态 | 耗时(s) | 五项命中 | 先健康检查 | 最终测试 | 状态已写回 | 未越界 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {status} | {seconds} | {hits} | {health_check_first} | {final_test_passed} | {state_written_back} | {stayed_in_workspace} |".format(**row)
        )
    lines.append("")

    report = ROOT / "instructor/d1/handoff/PRERUN-REPORT.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

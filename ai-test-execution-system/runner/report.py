"""从真实 artifacts 生成简单 Markdown Report。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _duration(started_at: str, finished_at: str) -> float:
    start = datetime.fromisoformat(started_at)
    finish = datetime.fromisoformat(finished_at)
    return round((finish - start).total_seconds(), 3)


def _retry_count(scenario_dir: Path) -> int:
    history = scenario_dir / "retry_history.json"
    if not history.is_file():
        return 0
    attempts = _read_json(history).get("attempts", [])
    return max(len(attempts) - 1, 0)


def build_report(run_dir: Path, output_path: Path) -> Dict[str, Any]:
    """读取 run.json 与每个 scenario/result.json，计算报告数字并写出 Markdown。"""
    run = _read_json(run_dir / "run.json")
    scenarios: List[Dict[str, Any]] = []
    for item in run["scenarios"]:
        scenario_dir = run_dir / "cases" / item["scenario_id"]
        result = _read_json(scenario_dir / "result.json")
        scenarios.append(
            {
                "scenario_id": item["scenario_id"],
                "result": result.get("result", "FAIL"),
                "duration": _duration(result["started_at"], result["finished_at"]),
                "evidence": str(scenario_dir.relative_to(run_dir)),
                "retry_count": _retry_count(scenario_dir),
                "error": result.get("error"),
            }
        )
    total = len(scenarios)
    passed = sum(item["result"] == "PASS" for item in scenarios)
    failed = total - passed
    report = {
        "run_id": run["run_id"],
        "suite": run["suite"],
        "start": run["started_at"],
        "finish": run["finished_at"],
        "duration": _duration(run["started_at"], run["finished_at"]),
        "total": total,
        "passed": passed,
        "failed": failed,
        "scenarios": scenarios,
    }
    lines = [
        "# Round 4 Run Report",
        "",
        "- run_id: `{0}`".format(report["run_id"]),
        "- suite: `{0}`".format(report["suite"]),
        "- start: `{0}`".format(report["start"]),
        "- finish: `{0}`".format(report["finish"]),
        "- duration: `{0}s`".format(report["duration"]),
        "- total: **{0}**".format(total),
        "- passed: **{0}**".format(passed),
        "- failed: **{0}**".format(failed),
        "",
        "## Scenarios",
        "",
        "| scenario | result | duration | retry count | evidence |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for item in scenarios:
        lines.append(
            "| `{scenario_id}` | **{result}** | {duration}s | {retry_count} | `{evidence}` |".format(**item)
        )
    lines.extend(["", "## Needs attention", ""])
    failures = [item for item in scenarios if item["result"] != "PASS"]
    if failures:
        for item in failures:
            detail = ": {0}".format(item["error"]) if item.get("error") else ""
            lines.append("- `{0}` is **FAIL**{1}; inspect `{2}`.".format(item["scenario_id"], detail, item["evidence"]))
    else:
        lines.append("- None")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

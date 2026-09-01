#!/usr/bin/env python3
"""从 Plan、trace 和实际 workspace evidence 输出 D1 三级对照。"""
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path


SIGNALS = {
    "识别现有架构约束": ("repository", "service", "ExportQueue", "export queue", "tenant", "分页"),
    "遵守项目代码规范": ("API 层", "service.py", "不引入", "第三方", "无关重构", "复用"),
    "明确修改边界": ("app/main.py", "app/financing/service.py", "static/index.html", "只修改", "修改边界"),
    "明确验证方式": ("pytest", "测试", "验证", "git diff", "自检"),
}


def cell(value: object, width: int = 42) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value) or "无"
    value = str(value).replace("\n", " ")
    return value if len(value) <= width else value[: width - 1] + "…"


def plan_path(root: Path, level: str) -> Path:
    saved = root / level / "plan.md"
    return saved if saved.exists() else root / f"latest-{level}" / "plan.md"


def plan_diff(before: Path, after: Path, title: str) -> str:
    if not before.exists() or not after.exists():
        return f"[{title}] 证据缺失：{before} 或 {after}\n"
    diff = difflib.unified_diff(
        before.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True),
        after.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True),
        fromfile=f"{title} before", tofile=f"{title} after",
    )
    return "".join(diff) or f"[{title}] 无文字差异\n"


def plan_has_signal(plan: str, terms: tuple[str, ...]) -> bool:
    lowered = plan.lower()
    return any(term.lower() in lowered for term in terms)


def capability(item: dict, plan: str, name: str) -> str:
    if name in SIGNALS:
        return "YES" if plan_has_signal(plan, SIGNALS[name]) else "?"
    if name == "任务显性 Plan":
        return "YES" if item.get("plan_present") else "NO"
    if name == "实际执行代码":
        return "YES" if item.get("code_changed") else "NO"
    if name == "主动运行测试":
        return "YES" if item.get("agent_ran_dev_tests") else "NO"
    if name == "检查 diff":
        return "YES" if item.get("agent_checked_diff") else "NO"
    raise ValueError(f"unknown capability: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level1", type=Path, required=True)
    parser.add_argument("--level2", type=Path, required=True)
    parser.add_argument("--level3", type=Path, required=True)
    parser.add_argument("--plans-root", type=Path, required=True)
    parser.add_argument("--evidence-label", default="LIVE")
    args = parser.parse_args()
    evidence = {
        level: json.loads(path.read_text(encoding="utf-8"))
        for level, path in (("level1", args.level1), ("level2", args.level2), ("level3", args.level3))
    }
    plans = {level: plan_path(args.plans_root, level) for level in evidence}
    plan_text = {level: path.read_text(encoding="utf-8", errors="replace") if path.exists() else "" for level, path in plans.items()}
    names = ("任务显性 Plan", "识别现有架构约束", "遵守项目代码规范", "明确修改边界", "明确验证方式", "实际执行代码", "主动运行测试", "检查 diff")

    print("D1｜工程环境如何改变 AI 开发")
    print(f"\n证据类型：{args.evidence_label}")
    print("核心链条：先看清任务 → 再看懂项目 → 最后知道怎么交付\n")
    print(f"{'课堂证据':<24}{'Level 1':<12}{'Level 2':<12}{'Level 3'}")
    print("-" * 62)
    for name in names:
        values = [capability(evidence[level], plan_text[level], name) for level in ("level1", "level2", "level3")]
        print(f"{name:<22}{values[0]:<12}{values[1]:<12}{values[2]}")
    print("\nPlan 证据文件：")
    for level in ("level1", "level2", "level3"):
        print(f"  {level}: {plans[level]}")
    print("\n--- Plan v1 → Plan v2 ---")
    print(plan_diff(plans["level1"], plans["level2"], "Plan v1 → Plan v2"), end="")
    print("--- Plan v2 → Plan v3 ---")
    print(plan_diff(plans["level2"], plans["level3"], "Plan v2 → Plan v3"), end="")
    level3 = evidence["level3"]
    print("\nLevel 3 实际交付证据：")
    print(f"  修改文件：{cell(level3.get('files_changed', []), 100)}")
    print(f"  Agent 主动执行 pytest：{capability(level3, plan_text['level3'], '主动运行测试')}")
    print(f"  开发测试结果：{level3.get('dev_test_summary', '未记录')}")
    print(f"  diff：{level3.get('diff', '未记录')}")
    print(f"  自检结果：{json.dumps(level3.get('self_check', {}), ensure_ascii=False)}")
    print(f"  最终完成说明：{level3.get('final_message', '未记录')}")
    print("\n最后一问：Plan 有了，项目规则有了，自检也全绿了——现在能相信它了吗？")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

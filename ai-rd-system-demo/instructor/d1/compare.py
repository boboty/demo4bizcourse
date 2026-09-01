#!/usr/bin/env python3
"""输出三级递进表和 Plan v1/v2/v3 可读 diff。"""
from __future__ import annotations
import argparse, difflib, json
from pathlib import Path


def cell(value: object, width: int = 42) -> str:
    if isinstance(value, list): value = ", ".join(str(item) for item in value) or "无"
    value = str(value).replace("\n", " ")
    return value if len(value) <= width else value[:width - 1] + "…"


def plan_path(root: Path, level: str) -> Path:
    saved = root / level / "plan.md"
    return saved if saved.exists() else root / f"latest-{level}" / "plan.md"


def plan_diff(before: Path, after: Path, title: str) -> str:
    if not before.exists() or not after.exists(): return f"[{title}] 证据缺失：{before} 或 {after}\n"
    diff = difflib.unified_diff(before.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True), after.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True), fromfile=f"{title} before", tofile=f"{title} after")
    return "".join(diff) or f"[{title}] 无文字差异\n"


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--level1", type=Path, required=True); parser.add_argument("--level2", type=Path, required=True); parser.add_argument("--level3", type=Path, required=True); parser.add_argument("--plans-root", type=Path, required=True); parser.add_argument("--evidence-label", default="LIVE"); args = parser.parse_args()
    evidence = {level: json.loads(path.read_text(encoding="utf-8")) for level, path in (("level1", args.level1), ("level2", args.level2), ("level3", args.level3))}; l1, l2, l3 = (evidence[level] for level in ("level1", "level2", "level3"))
    rows = [("任务显性 Plan", "YES" if l1["plan_present"] else "NO", "YES" if l2["plan_present"] else "NO", "YES" if l3["plan_present"] else "NO"), ("识别现有架构约束", "?", "YES", "YES"), ("遵守项目代码规范", "?", "YES", "YES"), ("明确修改边界", "?", "YES", "YES"), ("明确验证方式", "?", "?", "YES"), ("实际执行代码", "NO", "NO", "YES" if l3["phase"] == "execute" else "NO"), ("主动运行测试", "NO", "NO", "YES" if l3.get("agent_ran_dev_tests") else "NO"), ("检查 diff", "NO", "NO", "YES" if l3.get("agent_checked_diff") else "NO")]
    print("D1｜工程环境如何改变 AI 开发\n\n证据类型：" + args.evidence_label + "\n核心链条：先看清任务 → 再看懂项目 → 最后知道怎么交付\n")
    print(f"{'课堂证据':<24}{'Level 1':<12}{'Level 2':<12}{'Level 3'}\n" + "-" * 62)
    for title, *values in rows: print(f"{title:<22}{values[0]:<12}{values[1]:<12}{values[2]}")
    print("\nPlan 证据文件：")
    for level in ("level1", "level2", "level3"): print(f"  {level}: {plan_path(args.plans_root, level)}")
    print("\n--- Plan v1 → Plan v2 ---")
    print(plan_diff(plan_path(args.plans_root, "level1"), plan_path(args.plans_root, "level2"), "Plan v1 → Plan v2"), end="")
    print("--- Plan v2 → Plan v3 ---")
    print(plan_diff(plan_path(args.plans_root, "level2"), plan_path(args.plans_root, "level3"), "Plan v2 → Plan v3"), end="")
    print("\nLevel 3 实际交付证据：")
    print(f"  修改文件：{cell(l3.get('files_changed', []), 100)}\n  Agent 主动执行 pytest：{'YES' if l3.get('agent_ran_dev_tests') else 'NO'}\n  开发测试结果：{l3.get('dev_test_summary', '未记录')}\n  diff：{l3.get('diff', '未记录')}\n  自检结果：{json.dumps(l3.get('self_check', {}), ensure_ascii=False)}\n  最终完成说明：{l3.get('final_message', '未记录')}")
    print("\n最后一问：Plan 有了，项目规则有了，自检也全绿了——现在能相信它了吗？")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

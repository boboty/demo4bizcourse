#!/usr/bin/env python3
"""输出课堂投屏使用的 D1 A/B 证据表。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def cell(value: object, width: int = 42) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value) or "无"
    value = str(value).replace("\n", " ")
    return value if len(value) <= width else value[: width - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    args = parser.parse_args()
    a = json.loads(args.a.read_text(encoding="utf-8"))
    b = json.loads(args.b.read_text(encoding="utf-8"))
    controlled = (
        a["baseline_digest"] == b["baseline_digest"]
        and a["baseline_digest"] == a["manifest"].get("baseline_digest")
        and b["baseline_digest"] == b["manifest"].get("baseline_digest")
        and a["manifest"].get("baseline_digest") == a["manifest"].get("workspace_initial_digest")
        and b["manifest"].get("baseline_digest") == b["manifest"].get("workspace_initial_digest")
        and a["manifest"].get("task_sha256") == b["manifest"].get("task_sha256")
        and a["manifest"].get("model") == b["manifest"].get("model")
        and a["manifest"].get("reasoning_effort") == b["manifest"].get("reasoning_effort")
        and a["manifest"].get("data_sha256") == b["manifest"].get("data_sha256")
        and a["manifest"].get("acceptance_sha256") == b["manifest"].get("acceptance_sha256")
        and a["manifest"].get("source_bundle_sha256")
        and a["manifest"].get("source_bundle_baseline_match") is True
    )
    rows = [
        ("模型", a["manifest"].get("model"), b["manifest"].get("model")),
        ("任务", "SAME", "SAME"),
        ("项目 baseline", "SAME", "SAME"),
        ("模型响应 / Codex 执行", "成功" if a.get("api_success") else "失败：" + str(a.get("api_error", "未知")), "成功" if b.get("codex_exit") == 0 else f"失败（exit {b.get('codex_exit')}）"),
        ("可检查项目", "是" if a["tool_capabilities"].get("inspect") else "否", "是" if b["tool_capabilities"].get("inspect") else "否"),
        ("可修改 workspace", "是" if a["tool_capabilities"].get("modify") else "否", "是" if b["tool_capabilities"].get("modify") else "否"),
        ("可执行命令", "是" if a["tool_capabilities"].get("commands") else "否", "是" if b["tool_capabilities"].get("commands") else "否"),
        ("可运行测试", "是" if a["tool_capabilities"].get("tests") else "否", "是" if b["tool_capabilities"].get("tests") else "否"),
        ("先读取的上下文", a["first_context_reads"], b["first_context_reads"]),
        ("计划 / 提案", "有" if a["plan_evidence"] else "未记录", "有" if b["plan_evidence"] else "未记录"),
        ("工程工具调用", a["engineering_tools"], b["engineering_tools"]),
        ("Agent 主动跑开发测试", "是" if a["agent_ran_dev_tests"] else "否", "是" if b["agent_ran_dev_tests"] else "否"),
        ("修改文件", a["files_changed"], b["files_changed"]),
        ("最终开发测试", a["dev_test_summary"], b["dev_test_summary"]),
        ("独立业务验收", "PASS" if a["independent_acceptance_passed"] else "BLOCKER", "PASS" if b["independent_acceptance_passed"] else "BLOCKER"),
        ("越界修改", a["boundary_violations"], b["boundary_violations"]),
        ("最终结果", "PASS" if a["dev_test_passed"] and a["independent_acceptance_passed"] else "BLOCKER", "PASS" if b["dev_test_passed"] and b["independent_acceptance_passed"] else "BLOCKER"),
    ]
    print("D1 Harness Comparison")
    print()
    print("控制变量：" + ("一致" if controlled else "BLOCKER：baseline / task / model / reasoning 不一致"))
    print(f"任务哈希：{a['manifest'].get('task_sha256')}")
    print(f"模型 / 推理档位：{a['manifest'].get('model')} / {a['manifest'].get('reasoning_effort')}")
    print()
    print(f"{'证据':<22}{'Harness A':<44}Harness B")
    print("-" * 110)
    for title, a_value, b_value in rows:
        print(f"{title:<18}{cell(a_value):<44}{cell(b_value)}")
    print()
    print(f"详细证据：{args.a}  |  {args.b}")
    return 0 if controlled else 1


if __name__ == "__main__":
    raise SystemExit(main())

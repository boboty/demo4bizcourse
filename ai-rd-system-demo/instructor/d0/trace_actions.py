#!/usr/bin/env python3
"""把 Agent 轨迹还原成有序动作序列，用于判断课堂链路是否真实发生。

支持 D0 runner 的两种轨迹格式：Codex `exec --json` 与 Claude Code `--output-format stream-json`。
只做事实提取：哪些命令跑过、什么时候改的文件、每次测试的退出码。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

TEST_PATTERN = re.compile(r"\bpytest\b")
READ_PATTERN = re.compile(r"\b(rg|grep|sed|cat|ls|find|head|tail)\b")
FAILED_PATTERN = re.compile(r"(\d+) failed")
PASSED_PATTERN = re.compile(r"(\d+) passed")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "str_replace_editor"}


def pytest_outcome(exit_code: int | None, output: str) -> str | None:
    """测试命令被 `&&` 串联时退出码可能来自后续命令，以 pytest 自己的汇总行为准。"""
    if FAILED_PATTERN.search(output):
        return "FAIL"
    if PASSED_PATTERN.search(output):
        return "PASS"
    if exit_code is None:
        return None
    return "PASS" if exit_code == 0 else "FAIL"


def _codex_actions(event: dict) -> list[dict]:
    if event.get("type") != "item.completed":
        return []
    item = event.get("item") or {}
    kind = item.get("type")
    if kind == "command_execution":
        exit_code = item.get("exit_code")
        try:
            exit_code = int(exit_code)
        except (TypeError, ValueError):
            exit_code = None
        return [
            {
                "kind": "command",
                "command": item.get("command", ""),
                "exit_code": exit_code,
                "output": item.get("aggregated_output", "") or "",
            }
        ]
    if kind == "file_change":
        return [{"kind": "edit", "paths": [str(item.get("changes", ""))[:200]]}]
    if kind == "agent_message":
        return [{"kind": "message", "text": item.get("text", "")}]
    return []


def _claude_actions(event: dict) -> list[dict]:
    if event.get("type") != "assistant":
        return []
    actions: list[dict] = []
    for block in (event.get("message") or {}).get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and block.get("text"):
            actions.append({"kind": "message", "text": block["text"]})
        if block.get("type") != "tool_use":
            continue
        name = block.get("name", "")
        payload = block.get("input") or {}
        if name == "Bash":
            actions.append({"kind": "command", "command": payload.get("command", ""), "exit_code": None, "output": ""})
        elif name in EDIT_TOOLS:
            actions.append({"kind": "edit", "paths": [str(payload.get("file_path", ""))]})
        elif name in {"Read", "Grep", "Glob"}:
            actions.append({"kind": "read", "tool": name})
    return actions


def actions(trace: Path) -> list[dict]:
    found: list[dict] = []
    if not trace.exists():
        return found
    for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        found.extend(_codex_actions(event))
        found.extend(_claude_actions(event))
    return found


def loop_facts(trace: Path) -> dict:
    """判断课堂链路：先读/搜 → 跑测试看到失败 → 改代码 → 再跑测试变绿。"""
    steps = actions(trace)
    first_edit = next((index for index, step in enumerate(steps) if step["kind"] == "edit"), None)

    def is_test_run(step: dict) -> bool:
        return step["kind"] == "command" and bool(TEST_PATTERN.search(step["command"]))

    def outcome(step: dict) -> str | None:
        return pytest_outcome(step.get("exit_code"), step.get("output", ""))

    test_runs = [(index, step) for index, step in enumerate(steps) if is_test_run(step)]
    failing_runs_before_edit = [
        step
        for index, step in test_runs
        if first_edit is not None and index < first_edit and outcome(step) == "FAIL"
    ]
    green_runs_after_edit = [
        step for index, step in test_runs if first_edit is not None and index > first_edit and outcome(step) == "PASS"
    ]
    read_or_search_before_edit = any(
        step["kind"] == "read" or (step["kind"] == "command" and READ_PATTERN.search(step["command"]))
        for index, step in enumerate(steps)
        if first_edit is not None and index < first_edit
    )

    sequence: list[str] = []
    for step in steps:
        if step["kind"] == "edit":
            label = "Edit"
        elif step["kind"] == "read":
            label = "Read/Search"
        elif step["kind"] == "command" and TEST_PATTERN.search(step["command"]):
            label = {"FAIL": "Run(FAIL)", "PASS": "Run(PASS)"}.get(outcome(step), "Run")
        elif step["kind"] == "command" and READ_PATTERN.search(step["command"]):
            label = "Read/Search"
        elif step["kind"] == "command":
            label = "Shell"
        else:
            continue
        if not sequence or sequence[-1] != label:
            sequence.append(label)

    return {
        "actions": sequence,
        "test_run_count": len(test_runs),
        "first_test_run_before_edit": bool(test_runs) and first_edit is not None and test_runs[0][0] < first_edit,
        "observed_failure_before_edit": bool(failing_runs_before_edit),
        "green_test_run_after_edit": bool(green_runs_after_edit),
        "read_or_search_before_edit": read_or_search_before_edit,
        "edited": first_edit is not None,
    }

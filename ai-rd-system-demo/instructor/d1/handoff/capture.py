#!/usr/bin/env python3
"""把一次 D1 工程现场接力（fresh session handoff）运行整理成课堂证据。

不做二选一的 PASS/FAIL，而是分别记录五个课堂预测是否命中，供现场讨论
"没命中的项说明工程现场还缺什么"。复用 instructor/d0/trace_actions.py 的
动作抽取，不重复造轮子。
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "instructor/d0"))
from trace_actions import actions  # noqa: E402

CHECKPOINT = ROOT / "instructor/baselines/d1-handoff/stage-1"
IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__", ".venv"}

FORBIDDEN_REFERENCES = (
    "d0-first-loop", "d1-level1", "d1-level2", "d1-level3",
    "demo12-financing", "demo3-developer", "demo3-fixed", "demo3-validator",
    "demo4-learned", "demo4-sedimentation", "independent_acceptance.py",
    "instructor/reference", "instructor/golden",
)


def source_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts)
    }


def write_diff(workspace: Path, output: Path) -> list[str]:
    baseline, current = source_files(CHECKPOINT), source_files(workspace)
    changed = sorted(name for name in baseline.keys() | current.keys() if baseline.get(name) != current.get(name))
    lines: list[str] = []
    for name in changed:
        before = baseline.get(name, b"").decode("utf-8", errors="replace").splitlines(keepends=True)
        after = current.get(name, b"").decode("utf-8", errors="replace").splitlines(keepends=True)
        lines.extend(difflib.unified_diff(before, after, fromfile=f"handoff/{name}", tofile=f"workspace/{name}"))
    output.write_text("".join(lines), encoding="utf-8")
    return changed


def pytest_summary(workspace: Path) -> tuple[int, str]:
    python = ROOT / ".venv/bin/python"
    if not python.exists():
        python = Path("python3")
    result = subprocess.run(
        [str(python), "-m", "pytest", "-q"], cwd=workspace, text=True, capture_output=True, check=False
    )
    output = (result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or ["无输出"])[-1]
    return result.returncode, output


def command_texts(steps: list[dict]) -> list[str]:
    return [step["command"] for step in steps if step["kind"] == "command"]


def message_texts(steps: list[dict]) -> list[str]:
    return [step["text"] for step in steps if step["kind"] == "message" and step.get("text")]


def any_contains(haystacks: list[str], needle_pattern: re.Pattern[str]) -> bool:
    return any(needle_pattern.search(text) for text in haystacks)


VERIFY_RUN_PATTERN = re.compile(r"(^|[\s;&|])(\./)?verify\.sh\b|bash\s+verify\.sh|sh\s+verify\.sh")
PYTEST_RUN_PATTERN = re.compile(r"\bpytest\b")
GIT_LOG_PATTERN = re.compile(r"\bgit\s+log\b")


def score_predictions(steps: list[dict], final_message: str, diff_text: str) -> dict[str, Any]:
    commands = command_texts(steps)
    messages = message_texts(steps) + ([final_message] if final_message else [])
    all_text = "\n".join(commands + messages).lower()

    read_task = any_contains(commands, re.compile(r"task\.md", re.I))
    read_progress = any_contains(commands, re.compile(r"progress\.md", re.I))
    read_decisions = any_contains(commands, re.compile(r"decisions\.md", re.I))
    read_features = any_contains(commands, re.compile(r"feature-list\.json", re.I))
    read_git_log = any_contains(commands, GIT_LOG_PATTERN)

    mentions_customer = any(token in all_text for token in ("customer_name", "客户名称", "customer name"))
    mentions_status_word = any(token in all_text for token in ("status", "状态"))
    mentions_export = any(token in all_text for token in ("export", "导出"))

    ran_verify_script = any_contains(commands, VERIFY_RUN_PATTERN)
    ran_pytest_directly = any_contains(commands, PYTEST_RUN_PATTERN) and not ran_verify_script

    mentions_done_customer_filter = ("customer_name" in all_text or "客户名称" in all_text) and any(
        token in all_text for token in ("已完成", "已经实现", "done", "已实现", "已经完成", "上一个 session", "上一轮")
    )

    diff_lower = diff_text.lower()
    implemented_status_filter = bool(re.search(r"\+.*def _filter_by_status", diff_text)) or bool(
        re.search(r"\+\s*status\s*:\s*optional\[str\]", diff_lower)
    )
    implemented_export_route = "post" in diff_lower and "/export" in diff_lower
    next_step_code_evidence = implemented_status_filter or implemented_export_route
    next_step_message_evidence = mentions_status_word and mentions_export and (
        "下一步" in all_text or "next" in all_text or "接下来" in all_text or "还需要" in all_text or "未完成" in all_text
    )

    decision_message_evidence = any(token in all_text for token in ("d-001", "d-002", "d-003")) or (
        ("权限" in all_text and "分页" in all_text) or ("大小写" in all_text and "子串" in all_text)
    )

    predictions = {
        "1_identified_task": {
            "hit": bool(read_task or (mentions_customer and mentions_status_word and mentions_export)),
            "evidence": {"read_task_md": read_task, "message_mentions_all_three_scopes": mentions_customer and mentions_status_word and mentions_export},
        },
        "2_identified_done": {
            "hit": bool(read_progress or read_features or mentions_done_customer_filter),
            "evidence": {"read_progress_md": read_progress, "read_feature_list_json": read_features, "message_states_customer_filter_done": mentions_done_customer_filter},
        },
        "3_identified_next_step": {
            "hit": bool(next_step_code_evidence or next_step_message_evidence),
            "evidence": {
                "implemented_status_filter_in_diff": implemented_status_filter,
                "implemented_export_route_in_diff": implemented_export_route,
                "message_names_next_step": next_step_message_evidence,
            },
        },
        "4_identified_decision": {
            "hit": bool(read_decisions or decision_message_evidence),
            "evidence": {"read_decisions_md": read_decisions, "message_references_a_decision": decision_message_evidence},
        },
        "5_correct_verify_command": {
            "hit": bool(ran_verify_script),
            "evidence": {"ran_verify_sh": ran_verify_script, "ran_pytest_directly_instead": ran_pytest_directly},
        },
        "read_git_log": read_git_log,
    }
    predictions["hits"] = sum(1 for key, value in predictions.items() if isinstance(value, dict) and value["hit"])
    predictions["total"] = 5
    return predictions


def boundary_violations(steps: list[dict]) -> list[str]:
    commands = command_texts(steps)
    found = []
    for command in commands:
        for token in FORBIDDEN_REFERENCES:
            if token in command:
                found.append(f"{token}: {command.strip()[:160]}")
    return found


def health_check_timing(steps: list[dict]) -> dict[str, Any]:
    first_edit = next((index for index, step in enumerate(steps) if step["kind"] == "edit"), None)
    is_verify_or_test = lambda step: step["kind"] == "command" and (
        VERIFY_RUN_PATTERN.search(step["command"]) or PYTEST_RUN_PATTERN.search(step["command"])
    )
    verify_runs = [index for index, step in enumerate(steps) if is_verify_or_test(step)]
    return {
        "ran_verify_or_pytest_before_first_edit": bool(verify_runs) and (first_edit is None or verify_runs[0] < first_edit),
        "verify_or_pytest_run_count": len(verify_runs),
        "edited": first_edit is not None,
    }


def progress_written_back(workspace: Path) -> dict[str, bool]:
    checkpoint_progress = (CHECKPOINT / "PROGRESS.md").read_text(encoding="utf-8")
    workspace_progress = (workspace / "PROGRESS.md").read_text(encoding="utf-8") if (workspace / "PROGRESS.md").exists() else ""
    checkpoint_decisions = (CHECKPOINT / "DECISIONS.md").read_text(encoding="utf-8")
    workspace_decisions = (workspace / "DECISIONS.md").read_text(encoding="utf-8") if (workspace / "DECISIONS.md").exists() else ""
    return {
        "progress_md_changed": workspace_progress != checkpoint_progress,
        "decisions_md_changed": workspace_decisions != checkpoint_decisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--final-message", type=Path)
    parser.add_argument("--runner-status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    runner = json.loads(args.runner_status.read_text(encoding="utf-8"))
    steps = actions(args.trace)
    final_message = ""
    if args.final_message and args.final_message.exists():
        final_message = args.final_message.read_text(encoding="utf-8", errors="replace").strip()

    diff_path = args.output.parent / "workspace.diff"
    changed_files = write_diff(workspace, diff_path)
    diff_text = diff_path.read_text(encoding="utf-8")
    test_code, test_summary = pytest_summary(workspace)

    predictions = score_predictions(steps, final_message, diff_text)
    violations = boundary_violations(steps)
    timing = health_check_timing(steps)
    state_written_back = progress_written_back(workspace)

    result = {
        "run_status": runner.get("status", "FAILED"),
        "elapsed_seconds": runner.get("elapsed_seconds"),
        "final_message": final_message,
        "files_changed_since_handoff": changed_files,
        "final_test_passed": test_code == 0,
        "final_test_summary": test_summary,
        "predictions": predictions,
        "health_check_timing": timing,
        "state_written_back": state_written_back,
        "workspace_boundary_violations": violations,
        "stayed_in_workspace": not violations,
        "trace": str(args.trace),
        "diff": str(diff_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_status": result["run_status"],
                "elapsed_seconds": result["elapsed_seconds"],
                "predictions_hit": f"{predictions['hits']}/{predictions['total']}",
                "ran_health_check_first": timing["ran_verify_or_pytest_before_first_edit"],
                "final_test_passed": result["final_test_passed"],
                "state_written_back": state_written_back,
                "stayed_in_workspace": result["stayed_in_workspace"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

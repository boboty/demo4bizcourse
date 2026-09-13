#!/usr/bin/env python3
"""把一次 D0 现场运行整理成课堂证据，不调用任何独立验收器。"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trace_actions import loop_facts  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "instructor/baselines/d0-first-loop"
IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__", ".venv"}
D0_TEST_FILE = "tests/test_repayment_schedule.py"
D0_SOURCE_FILE = "app/repayment/service.py"


def source_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts)
    }


def digest(files: dict[str, bytes]) -> str:
    payload = [(name, hashlib.sha256(data).hexdigest()) for name, data in sorted(files.items())]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def commands_from(value: Any) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, child in value.items():
            if key in {"cmd", "command"} and isinstance(child, str):
                found.append(child)
            elif key in {"arguments", "input"} and isinstance(child, str):
                try:
                    found.extend(commands_from(json.loads(child)))
                except json.JSONDecodeError:
                    pass
            else:
                found.extend(commands_from(child))
        return found
    if isinstance(value, list):
        return [item for child in value for item in commands_from(child)]
    return []


def messages_from(value: Any) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        if value.get("type") in {"agent_message", "message", "text"}:
            for key in ("text", "message", "content"):
                if isinstance(value.get(key), str):
                    found.append(value[key])
                    break
        return found + [item for child in value.values() for item in messages_from(child)]
    if isinstance(value, list):
        return [item for child in value for item in messages_from(child)]
    return []


def trace_evidence(trace: Path) -> tuple[list[str], list[str]]:
    commands: list[str] = []
    messages: list[str] = []
    if not trace.exists():
        return commands, messages
    for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        commands.extend(commands_from(event))
        messages.extend(messages_from(event))
    return list(dict.fromkeys(item.strip() for item in commands if item.strip())), messages


def write_diff(workspace: Path, output: Path) -> list[str]:
    baseline, current = source_files(BASELINE), source_files(workspace)
    changed = sorted(name for name in baseline.keys() | current.keys() if baseline.get(name) != current.get(name))
    lines: list[str] = []
    for name in changed:
        before = baseline.get(name, b"").decode("utf-8", errors="replace").splitlines(keepends=True)
        after = current.get(name, b"").decode("utf-8", errors="replace").splitlines(keepends=True)
        lines.extend(difflib.unified_diff(before, after, fromfile=f"baseline/{name}", tofile=f"workspace/{name}"))
    output.write_text("".join(lines), encoding="utf-8")
    return changed


def pytest_summary(workspace: Path) -> tuple[int, str]:
    result = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or ["无输出"])[-1]
    return result.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--final-message", type=Path)
    parser.add_argument("--runner-status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", default="live")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    runner = json.loads(args.runner_status.read_text(encoding="utf-8"))
    commands, messages = trace_evidence(args.trace)
    final_message = ""
    if args.final_message and args.final_message.exists():
        final_message = args.final_message.read_text(encoding="utf-8", errors="replace").strip()
    if not final_message and messages:
        final_message = "\n".join(messages[-3:]).strip()

    changed = write_diff(workspace, args.output.parent / "workspace.diff")
    test_code, test_summary = pytest_summary(workspace)
    test_commands = [command for command in commands if "pytest" in command]
    loop = loop_facts(args.trace)

    result = {
        "loop": loop,
        "label": args.label,
        "agent": runner.get("agent", "codex"),
        "run_status": runner.get("status", "FAILED"),
        "elapsed_seconds": runner.get("elapsed_seconds"),
        "baseline_digest": digest(source_files(BASELINE)),
        "workspace_digest": digest(source_files(workspace)),
        "files_changed": changed,
        "d0_source_touched": D0_SOURCE_FILE in changed,
        "tests_modified": D0_TEST_FILE in changed,
        "engineering_commands": commands,
        "agent_ran_pytest": bool(test_commands),
        "agent_pytest_commands": test_commands,
        "final_test_passed": test_code == 0,
        "final_test_summary": test_summary,
        "final_message": final_message,
        "trace": str(args.trace),
        "diff": str(args.output.parent / "workspace.diff"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_status": result["run_status"],
                "elapsed_seconds": result["elapsed_seconds"],
                "loop": " → ".join(loop["actions"]),
                "observed_failure_before_edit": loop["observed_failure_before_edit"],
                "final_test_passed": result["final_test_passed"],
                "final_test_summary": result["final_test_summary"],
                "tests_modified": result["tests_modified"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

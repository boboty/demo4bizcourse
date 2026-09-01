#!/usr/bin/env python3
"""把一次 Codex CLI 运行与工作区外验收整理成可比较的证据。"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "instructor" / "baselines" / "demo12-financing"
IGNORED_PARTS = {".pytest_cache", "__pycache__", ".d1-harness"}
TEST_MARKERS = ("pytest",)
READ_MARKERS = ("rg ", "find ", "ls", "sed ", "cat ", "head ", "tree")
WRITE_MARKERS = ("apply_patch", ">", "tee ", "cp ", "mv ", "rm ", "python -c")


def source_files(root: Path) -> dict[str, bytes]:
    files = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts):
            files[str(relative)] = path.read_bytes()
    return files


def digest(files: dict[str, bytes]) -> str:
    payload = [(name, hashlib.sha256(data).hexdigest()) for name, data in sorted(files.items())]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def commands_from(value: Any) -> list[str]:
    commands: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"cmd", "command"} and isinstance(child, str):
                commands.append(child)
            elif key in {"arguments", "input"} and isinstance(child, str):
                try:
                    commands.extend(commands_from(json.loads(child)))
                except json.JSONDecodeError:
                    pass
            else:
                commands.extend(commands_from(child))
    elif isinstance(value, list):
        for child in value:
            commands.extend(commands_from(child))
    return commands


def messages_from(value: Any) -> list[str]:
    messages: list[str] = []
    if isinstance(value, dict):
        kind = value.get("type")
        if kind in {"agent_message", "message"}:
            for key in ("text", "message", "content"):
                text = value.get(key)
                if isinstance(text, str):
                    messages.append(text)
                    break
        for child in value.values():
            messages.extend(messages_from(child))
    elif isinstance(value, list):
        for child in value:
            messages.extend(messages_from(child))
    return messages


def trace_evidence(trace: Path) -> tuple[list[str], str]:
    commands: list[str] = []
    final_messages: list[str] = []
    if not trace.exists():
        return commands, ""
    for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        commands.extend(commands_from(event))
        final_messages.extend(messages_from(event))
    unique = list(dict.fromkeys(command.strip() for command in commands if command.strip()))
    return unique, "\n".join(final_messages[-3:])


def brief(commands: list[str], predicate, limit: int = 3) -> str:
    chosen = [command.replace("\n", " ") for command in commands if predicate(command)]
    return "； ".join(chosen[:limit]) if chosen else "未记录"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", choices=("a", "b"), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runner-exit", type=int, default=0)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    commands, final_message = trace_evidence(args.trace)
    test = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "pytest", "-q"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )
    acceptance = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "instructor" / "d1" / "independent_acceptance.py"), "--workspace", str(workspace), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        acceptance_result = json.loads(acceptance.stdout)
    except json.JSONDecodeError:
        acceptance_result = {"passed": False, "problems": ["验收器未产生 JSON"], "changed_files": [], "boundary_violations": []}
    changed = acceptance_result.get("changed_files", [])
    reads = brief(commands, lambda command: any(marker in command for marker in READ_MARKERS) and not any(marker in command for marker in WRITE_MARKERS))
    plan_markers = ("plan", "计划")
    has_plan = any(marker in command.lower() for command in commands for marker in plan_markers) or any(marker in final_message.lower() for marker in plan_markers)
    agent_test = any(marker in command for command in commands for marker in TEST_MARKERS)
    result = {
        "harness": args.harness.upper(),
        "manifest": manifest,
        "baseline_digest": digest(source_files(BASELINE)),
        "workspace_source_digest": digest(source_files(workspace)),
        "first_context_reads": reads,
        "plan_evidence": has_plan,
        "engineering_tools": brief(commands, lambda command: True, limit=8),
        "tool_capabilities": {"inspect": True, "modify": True, "commands": True, "tests": True},
        "agent_ran_dev_tests": agent_test,
        "files_changed": changed,
        "dev_test_passed": test.returncode == 0,
        "dev_test_summary": (test.stdout.strip().splitlines() or test.stderr.strip().splitlines() or ["无输出"])[-1],
        "independent_acceptance_passed": bool(acceptance_result.get("passed")),
        "independent_acceptance_problems": acceptance_result.get("problems", []),
        "boundary_violations": acceptance_result.get("boundary_violations", []),
        "final_message": final_message,
        "trace": str(args.trace),
        "codex_exit": args.runner_exit,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"captured {args.harness.upper()} evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

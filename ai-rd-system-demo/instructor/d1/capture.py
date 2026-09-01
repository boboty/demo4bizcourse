#!/usr/bin/env python3
"""把三级 Codex 运行整理成课堂证据，不调用独立验收器。"""
from __future__ import annotations
import argparse, difflib, hashlib, json, subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "instructor/baselines/demo12-financing"
IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__"}
EXPECTED_CHANGED_FILES = {"app/main.py", "app/financing/service.py", "static/index.html", "docs/api.md", "tests/test_financing_baseline.py"}


def source_files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file() and not IGNORED_PARTS.intersection(path.parts)}


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
        if value.get("type") in {"agent_message", "message"}:
            for key in ("text", "message", "content"):
                if isinstance(value.get(key), str):
                    found.append(value[key])
                    break
        return found + [item for child in value.values() for item in messages_from(child)]
    if isinstance(value, list):
        return [item for child in value for item in messages_from(child)]
    return []


def trace_evidence(*traces: Path | None) -> tuple[list[str], str]:
    commands: list[str] = []
    messages: list[str] = []
    for trace in traces:
        if not trace or not trace.exists():
            continue
        for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            commands.extend(commands_from(event)); messages.extend(messages_from(event))
    return list(dict.fromkeys(item.strip() for item in commands if item.strip())), "\n".join(messages[-5:])


def changed_paths(workspace: Path) -> list[str]:
    baseline, current = source_files(BASELINE), source_files(workspace)
    env_files = {"PROJECT-MEMORY.md", "CODING-STANDARDS.md", "SELF-CHECK.md"}
    return sorted(path for path in baseline.keys() | current.keys() if path not in env_files and baseline.get(path) != current.get(path))


def write_diff(workspace: Path, output: Path) -> None:
    baseline, current = source_files(BASELINE), source_files(workspace)
    environment_files = {"PROJECT-MEMORY.md", "CODING-STANDARDS.md", "SELF-CHECK.md"}
    lines: list[str] = []
    for name in sorted(baseline.keys() | current.keys()):
        if name in environment_files:
            continue
        before = baseline.get(name, b"").decode("utf-8", errors="replace").splitlines(keepends=True)
        after = current.get(name, b"").decode("utf-8", errors="replace").splitlines(keepends=True)
        if before != after:
            lines.extend(difflib.unified_diff(before, after, fromfile=f"baseline/{name}", tofile=f"workspace/{name}"))
    output.write_text("".join(lines), encoding="utf-8")


def test_summary(workspace: Path) -> tuple[int, str]:
    result = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q"], cwd=workspace, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or ["无输出"])[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=("level1", "level2", "level3"), required=True)
    parser.add_argument("--phase", choices=("plan", "execute"), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--execute-trace", type=Path)
    parser.add_argument("--final-message", type=Path)
    parser.add_argument("--runner-status", type=Path, required=True)
    parser.add_argument("--runner-exit", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")); runner = json.loads(args.runner_status.read_text(encoding="utf-8"))
    traces = [args.trace, args.execute_trace]; commands, final_message = trace_evidence(*traces)
    if args.final_message and args.final_message.exists():
        final_message = args.final_message.read_text(encoding="utf-8", errors="replace")
    changed = changed_paths(workspace); diff_path = args.output.parent / "workspace.diff"; write_diff(workspace, diff_path)
    plan_text = args.plan.read_text(encoding="utf-8", errors="replace") if args.plan.exists() else ""
    agent_ran_tests = any("pytest" in command for command in commands); agent_checked_diff = any("git diff" in command for command in commands)
    test_code: int | None = None; test_output = "未执行（Plan 阶段不运行测试）"
    if args.phase == "execute": test_code, test_output = test_summary(workspace)
    required_mentions = {
        "客户名称筛选": "客户名称" in final_message or "customer_name" in final_message,
        "融资状态筛选": "融资状态" in final_message or "status" in final_message,
        "组合筛选": "组合" in final_message or "同时" in final_message,
        "数据权限": "权限" in final_message or "tenant" in final_message,
        "异步导出": "导出" in final_message and ("队列" in final_message or "queue" in final_message.lower()),
        "diff 检查": agent_checked_diff,
    }
    self_check = {"适用": args.level == "level3" and args.phase == "execute", "agent_ran_pytest": agent_ran_tests, "postflight_pytest_passed": test_code == 0 if test_code is not None else None, "agent_checked_git_diff": agent_checked_diff, "changed_files_within_task_boundary": set(changed) <= EXPECTED_CHANGED_FILES, "required_completion_mentions": required_mentions}
    result = {
        "level": args.level, "phase": args.phase, "manifest": manifest, "baseline_digest": digest(source_files(BASELINE)),
        "workspace_initial_digest": digest(source_files(workspace)) if args.phase == "plan" else None,
        "plan_path": str(args.plan), "plan_sha256": hashlib.sha256(plan_text.encode()).hexdigest(), "plan_present": bool(plan_text.strip()),
        "files_changed": changed if args.phase == "execute" else [], "code_changed": bool(changed) if args.phase == "execute" else False,
        "agent_ran_dev_tests": agent_ran_tests if args.phase == "execute" else False, "agent_checked_diff": agent_checked_diff if args.phase == "execute" else False,
        "dev_test_passed": test_code == 0 if test_code is not None else None, "dev_test_summary": test_output,
        "self_check": self_check if args.phase == "execute" else {"适用": False, "原因": "Level 1/2 只保存 Plan，不执行代码"},
        "final_message": final_message, "engineering_commands": commands,
        "run_status": "PLAN_ONLY" if args.phase == "plan" else runner.get("status", "FAILED"), "codex_exit": args.runner_exit,
        "elapsed_seconds": runner.get("elapsed_seconds"), "trace": [str(path) for path in traces if path], "diff": str(diff_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"captured {args.level} {args.phase} evidence: {args.output}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())

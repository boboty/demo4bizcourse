#!/usr/bin/env python3
"""在 D0 workspace 里运行一个已登录的 Agent CLI，并保留超时与原始证据。

课堂默认使用 Codex（与 D1 一致）。若现场只有 Claude Code 已登录，可用
`--agent claude` 切换；两种 runner 使用相同的 workspace、任务文本和超时，
只更换执行环境，不更换任务。
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

AGENTS = ("codex", "claude")


def stop_group(process: subprocess.Popen[bytes], sig: int) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def build_command(agent: str, workspace: Path, prompt: str, last_message: Path) -> list[str]:
    if agent == "codex":
        return [
            "codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "workspace-write",
            "-C", str(workspace), "-o", str(last_message), prompt,
        ]
    return [
        "claude", "--print", prompt,
        "--output-format", "stream-json", "--verbose",
        "--permission-mode", "acceptEdits",
        # 不在这里预授权 Bash：`-p` 无人值守 + Bash 免审批 = 一个没有沙箱、
        # 也没有逐次确认的自动改代码回路。课堂用 Claude Code 请走交互会话。
        "--add-dir", str(workspace),
    ]


def claude_last_message(trace: Path) -> str:
    """从 stream-json 轨迹里取最后一条 result 文本。"""
    text = ""
    for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "result" and isinstance(event.get("result"), str):
            text = event["result"]
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--agent", choices=AGENTS, default="codex")
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--last-message", type=Path, required=True)
    parser.add_argument("--stderr", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--exit-code", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.timeout_seconds < 1:
        raise SystemExit("timeout-seconds must be >= 1")

    for path in (args.trace, args.last_message, args.stderr, args.status, args.exit_code):
        path.parent.mkdir(parents=True, exist_ok=True)
    workspace = args.workspace.resolve()
    command = build_command(args.agent, workspace, args.prompt.read_text(encoding="utf-8"), args.last_message)

    started = time.monotonic()
    with args.trace.open("wb") as trace, args.stderr.open("wb") as stderr:
        process = subprocess.Popen(
            command,
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            stdout=trace,
            stderr=stderr,
            start_new_session=True,
        )
        timed_out = False
        try:
            process.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_group(process, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                stop_group(process, signal.SIGKILL)
                process.wait()
    elapsed = round(time.monotonic() - started, 3)

    if args.agent == "claude" and not args.last_message.exists() and not timed_out:
        args.last_message.write_text(claude_last_message(args.trace), encoding="utf-8")

    status = "TIMEOUT" if timed_out else ("COMPLETED" if process.returncode == 0 else "FAILED")
    args.exit_code.write_text(f"{process.returncode}\n", encoding="utf-8")
    args.status.write_text(
        json.dumps(
            {
                "status": status,
                "agent": args.agent,
                "elapsed_seconds": elapsed,
                "timeout_seconds": args.timeout_seconds,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "agent": args.agent, "elapsed_seconds": elapsed, "exit_code": process.returncode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""运行已登录的 Codex CLI，并为 Plan/开发阶段保留超时与原始证据。"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def stop_group(process: subprocess.Popen[bytes], sig: int) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--last-message", type=Path, required=True)
    parser.add_argument("--stderr", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--exit-code", type=Path, required=True)
    parser.add_argument("--sandbox", choices=("read-only", "workspace-write"), required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    if args.timeout_seconds < 1:
        raise SystemExit("timeout-seconds must be >= 1")

    for path in (args.trace, args.last_message, args.stderr, args.status, args.exit_code):
        path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", args.sandbox,
        "-C", str(args.workspace), "-o", str(args.last_message),
        args.prompt.read_text(encoding="utf-8"),
    ]
    started = time.monotonic()
    with args.trace.open("wb") as trace, args.stderr.open("wb") as stderr:
        process = subprocess.Popen(
            command,
            cwd=args.workspace,
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
    status = "TIMEOUT" if timed_out else ("COMPLETED" if process.returncode == 0 else "FAILED")
    args.exit_code.write_text(f"{process.returncode}\n", encoding="utf-8")
    args.status.write_text(
        json.dumps({"status": status, "elapsed_seconds": elapsed, "timeout_seconds": args.timeout_seconds}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "elapsed_seconds": elapsed, "exit_code": process.returncode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

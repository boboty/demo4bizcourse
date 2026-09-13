#!/usr/bin/env bash
# D0 现场运行：reset → 启动 Agent → 保存证据。
# 用法：./scripts/d0_run.sh [--no-reset]
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
workspace="$repo_root/workspaces/d0-first-loop"
run_dir="$repo_root/instructor/d0/results/latest"
task_file="$repo_root/instructor/d0/task.txt"
agent="${D0_AGENT:-codex}"
timeout_seconds="${D0_TIMEOUT_SECONDS:-600}"

if [[ "${1:-}" != "--no-reset" ]]; then
  "$repo_root/scripts/reset_d0.sh"
fi

mkdir -p "$run_dir"
"$repo_root/.venv/bin/python" - "$repo_root/instructor/d0/prompts/execute.md" "$task_file" "$run_dir/prompt.md" <<'PY'
from pathlib import Path
import sys
template, task, output = map(Path, sys.argv[1:])
output.write_text(
    template.read_text(encoding="utf-8").replace("{TASK}", task.read_text(encoding="utf-8").strip()),
    encoding="utf-8",
)
PY

echo "D0：workspace 已就绪（起点为红灯），启动 Agent：$agent"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d0/agent_runner.py" \
  --agent "$agent" --workspace "$workspace" --prompt "$run_dir/prompt.md" \
  --trace "$run_dir/trace.jsonl" --last-message "$run_dir/final.md" \
  --stderr "$run_dir/stderr.log" --status "$run_dir/runner-status.json" \
  --exit-code "$run_dir/exit-code" --timeout-seconds "$timeout_seconds"

"$repo_root/.venv/bin/python" "$repo_root/instructor/d0/capture.py" \
  --workspace "$workspace" --trace "$run_dir/trace.jsonl" \
  --final-message "$run_dir/final.md" --runner-status "$run_dir/runner-status.json" \
  --output "$run_dir/result.json"

status="$("$repo_root/.venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$run_dir/runner-status.json")"
if [[ "$status" == "TIMEOUT" ]]; then exit 124; fi
exit 0

#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "level3" ]]; then
  echo "usage: scripts/d1_execute.sh level3" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
results="$repo_root/instructor/d1/results"
run_dir="$results/latest-level3"
workspace="$repo_root/workspaces/d1-level3"
task_file="$repo_root/instructor/d1/task.txt"
timeout_seconds="${D1_TIMEOUT_SECONDS:-180}"
if [[ ! -f "$run_dir/plan.md" || ! -f "$run_dir/manifest.json" ]]; then
  echo "请先运行 ./scripts/d1_plan.sh level3 保存 Plan v3" >&2
  exit 2
fi

"$repo_root/.venv/bin/python" - "$repo_root/instructor/d1/prompts/level3-execute.md" "$task_file" "$run_dir/execute-prompt.md" "$run_dir/plan.md" <<'PY'
from pathlib import Path
import sys
template, task, output, plan = map(Path, sys.argv[1:])
prompt = template.read_text(encoding="utf-8").replace("{TASK}", task.read_text(encoding="utf-8").strip())
output.write_text(prompt + "\n\n以下是刚刚保存的 Plan v3，请以它为本次开发的计划依据：\n\n" + plan.read_text(encoding="utf-8") + "\n", encoding="utf-8")
PY
echo "D1 Level 3：Plan v3 已保存，开始真实开发与开发侧自检"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/codex_runner.py" \
  --workspace "$workspace" --prompt "$run_dir/execute-prompt.md" \
  --trace "$run_dir/execute.trace.jsonl" --last-message "$run_dir/final.md" \
  --stderr "$run_dir/execute.stderr" --status "$run_dir/execute-status.json" \
  --exit-code "$run_dir/execute.exit-code" --sandbox workspace-write \
  --timeout-seconds "$timeout_seconds"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/capture.py" \
  --level level3 --phase execute --workspace "$workspace" \
  --manifest "$run_dir/manifest.json" --plan "$run_dir/plan.md" \
  --trace "$run_dir/plan.trace.jsonl" --execute-trace "$run_dir/execute.trace.jsonl" \
  --final-message "$run_dir/final.md" \
  --runner-status "$run_dir/execute-status.json" \
  --runner-exit "$(tr -d '[:space:]' < "$run_dir/execute.exit-code")" \
  --output "$run_dir/result.json"
status="$("$repo_root/.venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$run_dir/execute-status.json")"
if [[ "$status" == "TIMEOUT" ]]; then exit 124; fi
exit "$(tr -d '[:space:]' < "$run_dir/execute.exit-code")"

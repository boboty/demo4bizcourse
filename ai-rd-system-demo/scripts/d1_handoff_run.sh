#!/usr/bin/env bash
# D1 工程现场接力：reset → 全新 Codex session（无历史聊天记录）接手 → 保存证据。
# 用法：./scripts/d1_handoff_run.sh [--no-reset]
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
workspace="$repo_root/workspaces/d1-handoff"
run_dir="$repo_root/instructor/d1/handoff/results/latest"
prompt_file="$repo_root/instructor/d1/handoff/prompts/handoff.md"
timeout_seconds="${D1_HANDOFF_TIMEOUT_SECONDS:-300}"

if [[ "${1:-}" != "--no-reset" ]]; then
  "$repo_root/scripts/reset_d1_handoff.sh"
fi

mkdir -p "$run_dir"
cp "$prompt_file" "$run_dir/prompt.md"

echo "D1 工程现场接力：workspace 已就绪（3 个历史 commit，上一个 session 已结束），启动全新 Codex session"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/codex_runner.py" \
  --workspace "$workspace" --prompt "$run_dir/prompt.md" \
  --trace "$run_dir/trace.jsonl" --last-message "$run_dir/final.md" \
  --stderr "$run_dir/stderr.log" --status "$run_dir/runner-status.json" \
  --exit-code "$run_dir/exit-code" --sandbox workspace-write \
  --timeout-seconds "$timeout_seconds"

"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/handoff/capture.py" \
  --workspace "$workspace" --trace "$run_dir/trace.jsonl" \
  --final-message "$run_dir/final.md" --runner-status "$run_dir/runner-status.json" \
  --output "$run_dir/result.json"

status="$("$repo_root/.venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$run_dir/runner-status.json")"
if [[ "$status" == "TIMEOUT" ]]; then exit 124; fi
exit 0

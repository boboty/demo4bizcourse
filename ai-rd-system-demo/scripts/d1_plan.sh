#!/usr/bin/env bash
set -euo pipefail

level="${1:-}"
case "$level" in
  level1|level2|level3) ;;
  *) echo "usage: scripts/d1_plan.sh level1|level2|level3" >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
workspace="$repo_root/workspaces/d1-$level"
task_file="$repo_root/instructor/d1/task.txt"
prompt_template="$repo_root/instructor/d1/prompts/$level-plan.md"
results="$repo_root/instructor/d1/results"
timeout_seconds="${D1_TIMEOUT_SECONDS:-180}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$level"
run_dir="$results/$run_id"

"$repo_root/scripts/reset_d1.sh" "$level"
mkdir -p "$run_dir"
task_sha256="$(shasum -a 256 "$task_file" | awk '{print $1}')"
baseline_sha256="$(shasum -a 256 "$repo_root/instructor/baselines/demo12-financing/app/financing/data.json" | awk '{print $1}')"
environment_sha256="$(shasum -a 256 "$prompt_template" | awk '{print $1}')"
"$repo_root/.venv/bin/python" - "$prompt_template" "$task_file" "$run_dir/prompt.md" <<'PY'
from pathlib import Path
import sys
template, task, output = map(Path, sys.argv[1:])
output.write_text(template.read_text(encoding="utf-8").replace("{TASK}", task.read_text(encoding="utf-8").strip()) + "\n", encoding="utf-8")
PY
cat > "$run_dir/manifest.json" <<EOF
{
  "run_id": "$run_id",
  "level": "$level",
  "task_sha256": "$task_sha256",
  "baseline_data_sha256": "$baseline_sha256",
  "environment_prompt_sha256": "$environment_sha256",
  "task_source": "instructor/d1/task.txt",
  "workspace": "workspaces/d1-$level",
  "phase": "plan"
}
EOF

echo "D1 $level：只读 Plan，任务：$(tr -d '\n' < "$task_file")"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/codex_runner.py" \
  --workspace "$workspace" --prompt "$run_dir/prompt.md" \
  --trace "$run_dir/plan.trace.jsonl" --last-message "$run_dir/plan.md" \
  --stderr "$run_dir/plan.stderr" --status "$run_dir/plan-status.json" \
  --exit-code "$run_dir/plan.exit-code" --sandbox read-only \
  --timeout-seconds "$timeout_seconds"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/capture.py" \
  --level "$level" --phase plan --workspace "$workspace" \
  --manifest "$run_dir/manifest.json" --plan "$run_dir/plan.md" \
  --trace "$run_dir/plan.trace.jsonl" --runner-status "$run_dir/plan-status.json" \
  --runner-exit "$(tr -d '[:space:]' < "$run_dir/plan.exit-code")" \
  --output "$run_dir/result.json"
ln -sfn "$run_id" "$results/latest-$level"
echo "已保存 $level 的 Plan：$run_dir/plan.md"

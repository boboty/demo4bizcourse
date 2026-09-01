#!/usr/bin/env bash
set -euo pipefail

harness="${1:-}"
case "$harness" in
  a|b) ;;
  *) echo "usage: scripts/d1_run.sh a|b" >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
workspace="$repo_root/workspaces/d1-harness-$harness"
task_file="$repo_root/instructor/d1/task.txt"
results="$repo_root/instructor/d1/results"
model="${D1_MODEL:-gpt-5.6-luna}"
reasoning_effort="${D1_REASONING_EFFORT:-high}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$harness"
run_dir="$results/$run_id"

command -v codex >/dev/null || { echo "未找到 codex CLI" >&2; exit 1; }
"$repo_root/scripts/reset_d1.sh" "$harness"
mkdir -p "$run_dir"
export D1_BASELINE="$repo_root/instructor/baselines/demo12-financing"

task_sha256="$(shasum -a 256 "$task_file" | awk '{print $1}')"
data_sha256="$(shasum -a 256 "$workspace/app/financing/data.json" | awk '{print $1}')"
acceptance_sha256="$(shasum -a 256 "$repo_root/instructor/d1/independent_acceptance.py" | awk '{print $1}')"
source_digest() {
  "$repo_root/.venv/bin/python" -c 'from instructor.d1.capture import digest, source_files; from pathlib import Path; import sys; print(digest(source_files(Path(sys.argv[1]))))' "$1"
}
baseline_digest="$(cd "$repo_root" && source_digest "$D1_BASELINE")"
workspace_initial_digest="$(cd "$repo_root" && source_digest "$workspace")"
cat > "$run_dir/manifest.json" <<EOF
{
  "run_id": "$run_id",
  "harness": "${harness^^}",
  "model": "$model",
  "reasoning_effort": "$reasoning_effort",
  "task_sha256": "$task_sha256",
  "data_sha256": "$data_sha256",
  "acceptance_sha256": "$acceptance_sha256",
  "baseline_digest": "$baseline_digest",
  "workspace_initial_digest": "$workspace_initial_digest",
  "task_source": "instructor/d1/task.txt"
}
EOF

echo "D1 Harness ${harness^^}: model=$model, reasoning=$reasoning_effort"
echo "任务：$(cat "$task_file")"
set +e
codex exec --json --ephemeral --ignore-user-config --skip-git-repo-check \
  --model "$model" \
  -c "model_reasoning_effort=\"$reasoning_effort\"" \
  --sandbox workspace-write --approve-for-me \
  -C "$workspace" "$(cat "$task_file")" > "$run_dir/trace.jsonl" 2> "$run_dir/codex.stderr"
codex_status=$?
set -e
printf '%s\n' "$codex_status" > "$run_dir/codex.exit-code"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/capture.py" \
  --harness "$harness" --workspace "$workspace" --trace "$run_dir/trace.jsonl" \
  --manifest "$run_dir/manifest.json" --output "$run_dir/result.json"
ln -sfn "$run_id" "$results/latest-$harness"
echo "D1 Harness ${harness^^} complete (Codex exit: $codex_status)"
echo "evidence: $run_dir/result.json"
exit "$codex_status"

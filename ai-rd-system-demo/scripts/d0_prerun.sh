#!/usr/bin/env bash
# D0 稳定性预跑：重复 reset + 现场运行，逐次保存轨迹与摘要。
# 用法：./scripts/d0_prerun.sh [次数]，默认 10。
set -euo pipefail

count="${1:-10}"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
out="$repo_root/instructor/d0/preruns"
mkdir -p "$out"

for index in $(seq 1 "$count"); do
  run="$out/run-$(printf '%02d' "$index")"
  rm -rf "$run"
  if "$repo_root/scripts/d0_run.sh" > "$run.log" 2>&1; then
    :
  fi
  cp -R "$repo_root/instructor/d0/results/latest" "$run"
  cp "$run.log" "$run/run.log"
  echo "run $index: $(tail -1 "$run.log")"
done

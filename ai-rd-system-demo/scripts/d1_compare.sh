#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
results="$repo_root/instructor/d1/results"
a="$results/latest-a/result.json"
b="$results/latest-b/result.json"
if [[ ! -f "$a" || ! -f "$b" ]]; then
  echo "请先分别运行：./scripts/d1_run.sh a 和 ./scripts/d1_run.sh b" >&2
  exit 2
fi
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/compare.py" --a "$a" --b "$b"

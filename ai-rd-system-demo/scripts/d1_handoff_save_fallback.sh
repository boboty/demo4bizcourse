#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/handoff/save_fallback.py" \
  --source "$repo_root/instructor/d1/handoff/results/latest" \
  --destination "$repo_root/instructor/d1/handoff/fallback"

#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"; results="$repo_root/instructor/d1/results"
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/save_fallback.py" --source "$results" --destination "$repo_root/instructor/d1/fallback"

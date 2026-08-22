#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
fixed="$repo_root/instructor/baselines/demo3-fixed"
rsync -a --delete --exclude '.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' "$fixed/" "$repo_root/workspaces/demo3-developer/"
(cd "$repo_root/workspaces/demo3-developer" && python3 -m pytest -q tests/test_settlement_developer.py)
echo "restored Demo 3 fixed state"

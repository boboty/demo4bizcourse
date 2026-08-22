#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
"$repo_root/scripts/reset_demo2.sh"
reference="$repo_root/instructor/baselines/demo2-reference"
rsync -a --delete --exclude '.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' "$reference/" "$repo_root/workspaces/demo2-five-elements/"
(cd "$repo_root/workspaces/demo2-five-elements" && python3 -m pytest -q)
python3 "$repo_root/instructor/checks/task_a_acceptance.py"
echo "restored Demo 2 reference solution"

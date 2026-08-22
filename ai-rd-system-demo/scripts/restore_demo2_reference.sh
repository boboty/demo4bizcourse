#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
"$repo_root/scripts/reset_demo2.sh"
reference="$repo_root/instructor/baselines/demo12-reference"
workspace="$repo_root/workspaces/demo12-financing"
rsync -a --delete --exclude '.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' "$reference/" "$workspace/"
(cd "$workspace" && "$repo_root/.venv/bin/python" -m pytest -q)
"$repo_root/.venv/bin/python" "$repo_root/instructor/checks/task_a_acceptance.py"
echo "restored Demo 2 reference solution in demo12-financing"

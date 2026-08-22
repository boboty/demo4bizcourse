#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/reset_workspace.sh <workspace-name>" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
name="$1"
baseline="$repo_root/instructor/baselines/$name"
workspace="$repo_root/workspaces/$name"

if [[ ! -d "$baseline" || ! -d "$workspace" ]]; then
  echo "unknown workspace: $name" >&2
  exit 2
fi

rsync -a --delete \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  "$baseline/" "$workspace/"
echo "reset $name"

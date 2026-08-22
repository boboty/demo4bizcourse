#!/usr/bin/env bash
set -euo pipefail

name="${1:-capture}"
case "$name" in
  demo1) workspace_name=demo1-vague ;;
  demo2) workspace_name=demo2-five-elements ;;
  demo3-developer) workspace_name=demo3-developer ;;
  demo4) workspace_name=demo4-sedimentation ;;
  *) echo "usage: scripts/capture_diff.sh demo1|demo2|demo3-developer|demo4" >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$repo_root/instructor/captures"
diff -ru --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  "$repo_root/instructor/baselines/$workspace_name" \
  "$repo_root/workspaces/$workspace_name" \
  > "$repo_root/instructor/captures/$name.patch" || true
echo "saved instructor/captures/$name.patch"

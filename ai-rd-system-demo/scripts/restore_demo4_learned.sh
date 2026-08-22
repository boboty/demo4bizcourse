#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
workspace="$repo_root/workspaces/demo4-sedimentation"
cp "$repo_root/instructor/golden/AGENTS.learned.md" "$workspace/AGENTS.md"
cp "$repo_root/instructor/golden/validation_checklist.learned.md" "$workspace/validation/checklist.md"
echo "restored Demo 4 learned state"

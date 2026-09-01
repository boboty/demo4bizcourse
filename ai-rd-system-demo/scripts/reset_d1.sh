#!/usr/bin/env bash
set -euo pipefail

level="${1:-all}"
case "$level" in
  level1|level2|level3|all) ;;
  *) echo "usage: scripts/reset_d1.sh level1|level2|level3|all" >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
baseline="$repo_root/instructor/baselines/demo12-financing"

reset_one() {
  local current_level="$1"
  local workspace="$repo_root/workspaces/d1-$current_level"
  mkdir -p "$workspace"
  if [[ -d "$workspace/.git" ]]; then
    git -C "$workspace" reset --hard -q HEAD || true
    git -C "$workspace" clean -fdqx
  fi
  rsync -a --delete --exclude '.git/' --exclude '.pytest_cache/' --exclude '__pycache__/' "$baseline/" "$workspace/"
  if [[ "$current_level" != "level1" ]]; then
    cp "$repo_root/instructor/d1/environment/project-memory.md" "$workspace/PROJECT-MEMORY.md"
    cp "$repo_root/instructor/d1/environment/coding-standards.md" "$workspace/CODING-STANDARDS.md"
    if [[ "$current_level" == "level3" ]]; then
      cp "$repo_root/instructor/d1/environment/self-check.md" "$workspace/SELF-CHECK.md"
    fi
  fi
  if [[ ! -d "$workspace/.git" ]]; then
    git -C "$workspace" init -q
    git -C "$workspace" config user.email "d1@classroom.invalid"
    git -C "$workspace" config user.name "D1 Classroom"
  fi
  git -C "$workspace" add -A
  git -C "$workspace" commit --allow-empty -q -m "frozen D1 $current_level baseline"
  echo "reset d1-$current_level"
}

if [[ "$level" == "all" ]]; then
  reset_one level1
  reset_one level2
  reset_one level3
else
  reset_one "$level"
fi

#!/usr/bin/env bash
set -euo pipefail

target="${1:-both}"
case "$target" in
  a|b|both) ;;
  *) echo "usage: scripts/reset_d1.sh a|b|both" >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
baseline="$repo_root/instructor/baselines/demo12-financing"

reset_one() {
  local harness="$1"
  local workspace="$repo_root/workspaces/d1-harness-$harness"
  mkdir -p "$workspace"
  rsync -a --delete --exclude '.pytest_cache/' --exclude '__pycache__/' "$baseline/" "$workspace/"
  if [[ "$harness" == "b" ]]; then
    rsync -a "$repo_root/instructor/d1/harness-b/" "$workspace/"
    chmod +x "$workspace/tools/d1/context" "$workspace/tools/d1/plan" "$workspace/tools/d1/check" "$workspace/tools/d1/status"
  fi
  echo "reset d1-harness-$harness"
}

if [[ "$target" == "a" || "$target" == "both" ]]; then reset_one a; fi
if [[ "$target" == "b" || "$target" == "both" ]]; then reset_one b; fi

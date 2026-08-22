#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
"$repo_root/scripts/reset_demo3_developer.sh"
"$repo_root/scripts/reset_demo3_validator.sh"
(cd "$repo_root/workspaces/demo3-developer" && python3 -m pytest -q tests/test_settlement_developer.py)
echo "restored Demo 3 wrong/full-green state"

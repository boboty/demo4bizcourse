#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"; mode="${1:-live}"
if [[ "$mode" == "saved" ]]; then root="$repo_root/instructor/d1/fallback"; elif [[ "$mode" == "live" ]]; then root="$repo_root/instructor/d1/results"; else echo "usage: scripts/d1_compare.sh [live|saved]" >&2; exit 2; fi
for level in level1 level2 level3; do
  evidence_dir="$root/$level"
  if [[ "$mode" == "live" ]]; then evidence_dir="$root/latest-$level"; fi
  if [[ ! -f "$evidence_dir/result.json" ]]; then echo "缺少 $level 证据；请按 D1 Runbook 顺序运行。" >&2; exit 2; fi
done
label="LIVE"; [[ "$mode" == "saved" ]] && label="SAVED_EVIDENCE"
level1_dir="$root/level1"; level2_dir="$root/level2"; level3_dir="$root/level3"
if [[ "$mode" == "live" ]]; then level1_dir="$root/latest-level1"; level2_dir="$root/latest-level2"; level3_dir="$root/latest-level3"; fi
"$repo_root/.venv/bin/python" "$repo_root/instructor/d1/compare.py" --level1 "$level1_dir/result.json" --level2 "$level2_dir/result.json" --level3 "$level3_dir/result.json" --evidence-label "$label" --plans-root "$root"

#!/usr/bin/env bash
# D0 兜底：把 workspace 直接切到修复后的目标状态（8 passed）。
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
"$repo_root/scripts/reset_d0.sh"
cp "$repo_root/instructor/reference/d0_repayment_service.py" \
   "$repo_root/workspaces/d0-first-loop/app/repayment/service.py"
echo "d0-first-loop 已切到修复后的目标状态；如需回到起点请运行 ./scripts/reset_d0.sh"

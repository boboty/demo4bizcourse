#!/usr/bin/env bash
# D1 工程现场接力兜底：把 workspace 直接切到"下一步已完成"的目标状态。
# 只用于现场卡住时的讲解回放，永远不作为课堂 Agent 的起点。
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
workspace="$repo_root/workspaces/d1-handoff"
reference="$repo_root/instructor/reference/d1-handoff-completed"

"$repo_root/scripts/reset_d1_handoff.sh"
rsync -a --exclude '.git/' --exclude '__pycache__/' --exclude '.pytest_cache/' "$reference/" "$workspace/"
git -C "$workspace" add -A
git -C "$workspace" -c user.email="d1@classroom.invalid" -c user.name="D1 Classroom" commit -q -m "fixed: status filter + export completed (instructor fallback state)"
echo "d1-handoff 已切到状态筛选 + 导出均已完成的目标状态；如需回到接手起点请运行 ./scripts/reset_d1_handoff.sh"

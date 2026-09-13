#!/usr/bin/env bash
# D4 restore-sedimented：把 workspaces/demo4-sedimentation 直接切到"资产沉淀已完成"的
# 目标状态——规则资产（docs/rules/）、Golden Case（golden/）、统一 ./verify.sh 入口和
# 指向它们的工程记忆（AGENTS.md）都已就位。
#
# 用途：
#   1. live 沉淀会话（D4-2）失败或跑偏时的兜底；
#   2. D4-3/D4-4 需要一个确定性的"已沉淀"起点时直接使用，不必每次重新跑一次 Agent。
set -euo pipefail
repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
sedimented="${repo_root}/instructor/baselines/demo4-sedimented"
workspace="${repo_root}/workspaces/demo4-sedimentation"

rsync -a --delete --exclude '.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' \
  "${sedimented}/" "${workspace}/"
(cd "${workspace}" && ./verify.sh)
echo "restored Demo 4 sedimented state (workspace=${workspace})"
echo "如果 demo4_serve.sh 正在用 --reload 运行，改动会自动重启；如未生效，回到那个终端 Ctrl+C 后重新执行 ./scripts/demo4_serve.sh"

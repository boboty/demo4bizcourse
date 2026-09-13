#!/usr/bin/env bash
# D3 restore-fixed：把 workspaces/demo3-developer 直接切到"已按放款处理导出规则
# 修复"的目标状态——课堂 live fix 失败时的兜底，不是课堂主流程。
set -euo pipefail
repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
fixed="${repo_root}/instructor/baselines/demo3-fixed"
workspace="${repo_root}/workspaces/demo3-developer"

rsync -a --delete --exclude '.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' "${fixed}/" "${workspace}/"
(cd "${workspace}" && "${repo_root}/.venv/bin/python" -m pytest -q)
echo "restored Demo 3 fixed state (workspace=${workspace})"
echo "如果 demo3_serve.sh 正在用 --reload 运行，改动会自动重启；如未生效，回到那个终端 Ctrl+C 后重新执行 ./scripts/demo3_serve.sh"

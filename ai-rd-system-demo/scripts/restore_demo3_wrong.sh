#!/usr/bin/env bash
# D3 起点：把 developer / validator 两个 workspace 都重置为历史开发状态——
# 开发测试全绿，但放款导出仍然导出"当前筛选结果"（尚未见过导出规则）。
set -euo pipefail
repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
"${repo_root}/scripts/reset_demo3_developer.sh"
"${repo_root}/scripts/reset_demo3_validator.sh"
(cd "${repo_root}/workspaces/demo3-developer" && "${repo_root}/.venv/bin/python" -m pytest -q)
echo "restored Demo 3 wrong/full-green state"

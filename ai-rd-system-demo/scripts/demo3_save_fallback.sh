#!/usr/bin/env bash
# D3 fallback 快照：把当前 workspaces/demo3-developer 相对 baseline 的 diff、
# 开发测试结果、自检结果和独立验收结果存进 instructor/d3/fallback/，
# 供课堂现场 live fix 失败时直接展示"同一份修复真的发生过一次"的证据，
# 而不是另一个模拟结果。
#
# 用法（在 developer workspace 已经修复、demo3_serve.sh 仍在运行的情况下）：
#   ./scripts/demo3_save_fallback.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
workspace="${repo_root}/workspaces/demo3-developer"
fallback_dir="${repo_root}/instructor/d3/fallback"
base_url="${1:-http://127.0.0.1:8030}"

mkdir -p "${fallback_dir}"

diff -ru --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  "${repo_root}/instructor/baselines/demo3-developer" "${workspace}" \
  > "${fallback_dir}/workspace.diff" || true
echo "saved ${fallback_dir}/workspace.diff"

(cd "${workspace}" && "${repo_root}/.venv/bin/python" -m pytest -q) \
  > "${fallback_dir}/developer-tests-after.txt" 2>&1 || true
echo "saved ${fallback_dir}/developer-tests-after.txt"

(cd "${workspace}" && "${repo_root}/.venv/bin/python" bin/self-check) \
  > "${fallback_dir}/self-check-after.txt" 2>&1 || true
echo "saved ${fallback_dir}/self-check-after.txt"

if "${repo_root}/scripts/demo3_validator.sh" "${base_url}" > "${fallback_dir}/golden-after.txt" 2>&1; then
  echo "saved ${fallback_dir}/golden-after.txt (Overall: PASS)"
else
  echo "saved ${fallback_dir}/golden-after.txt (未达到 PASS，或开发服务未在 ${base_url} 运行——检查 demo3_serve.sh 是否还在跑)"
fi

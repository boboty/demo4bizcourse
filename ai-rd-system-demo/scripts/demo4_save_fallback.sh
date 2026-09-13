#!/usr/bin/env bash
# D4 fallback 快照：把当前 workspaces/demo4-sedimentation 相对未沉淀 baseline 的 diff，
# 以及沉淀态 PASS → 注入回归 BLOCK → 恢复后再次 PASS 的完整 ./verify.sh 输出，
# 存进 instructor/d4/fallback/，供课堂现场 live 沉淀失败时直接展示"这条资产链路真的跑通过一次"。
#
# 用法（在 workspaces/demo4-sedimentation 已经完成资产沉淀，或已运行
# ./scripts/restore_demo4_sedimented.sh 之后）：
#   ./scripts/demo4_save_fallback.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
workspace="${repo_root}/workspaces/demo4-sedimentation"
fallback_dir="${repo_root}/instructor/d4/fallback"

mkdir -p "${fallback_dir}"

diff -ru --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  "${repo_root}/instructor/baselines/demo4-sedimentation" "${workspace}" \
  > "${fallback_dir}/sedimentation.diff" || true
echo "saved ${fallback_dir}/sedimentation.diff"

if (cd "${workspace}" && ./verify.sh) > "${fallback_dir}/verify-sedimented.txt" 2>&1; then
  echo "saved ${fallback_dir}/verify-sedimented.txt (OVERALL: PASS)"
else
  echo "saved ${fallback_dir}/verify-sedimented.txt (未达到 PASS，检查沉淀是否完成)"
fi

"${repo_root}/scripts/inject_demo4_regression.sh" > "${fallback_dir}/inject.txt" 2>&1 || true
echo "saved ${fallback_dir}/inject.txt"

if (cd "${workspace}" && ./verify.sh) > "${fallback_dir}/verify-blocked.txt" 2>&1; then
  echo "saved ${fallback_dir}/verify-blocked.txt (WARNING：期望是 BLOCKED，但结果是 PASS，检查注入是否生效)"
else
  echo "saved ${fallback_dir}/verify-blocked.txt (OVERALL: BLOCKED，符合预期)"
fi

"${repo_root}/scripts/restore_demo4_fixed.sh" > "${fallback_dir}/restore.txt" 2>&1 || true
echo "saved ${fallback_dir}/restore.txt"

if (cd "${workspace}" && ./verify.sh) > "${fallback_dir}/verify-restored.txt" 2>&1; then
  echo "saved ${fallback_dir}/verify-restored.txt (OVERALL: PASS)"
else
  echo "saved ${fallback_dir}/verify-restored.txt (未恢复到 PASS，需要人工检查)"
fi

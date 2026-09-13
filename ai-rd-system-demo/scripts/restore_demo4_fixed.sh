#!/usr/bin/env bash
# D4 restore-fixed：撤销 inject_demo4_regression.sh 注入的历史回归，只恢复
# app/financing/service.py 的导出资格过滤逻辑，不触碰已经沉淀的规则 / Golden Case /
# verify.sh / AGENTS.md 资产——这是这次课堂想证明的事：修 bug 和沉淀资产是两件事。
#
# 用法：./scripts/restore_demo4_fixed.sh
set -euo pipefail
repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
workspace="${repo_root}/workspaces/demo4-sedimentation"
service_file="${workspace}/app/financing/service.py"

if [ ! -f "${service_file}" ]; then
  echo "找不到 ${service_file}" >&2
  exit 1
fi

if grep -q "DEMO4-INJECTED-REGRESSION" "${service_file}"; then
  python3 - "${service_file}" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
text = text.replace(
    "for row in rows]  # DEMO4-INJECTED-REGRESSION",
    "for row in eligible_rows]",
    1,
)
open(path, "w", encoding="utf-8").write(text)
PY
  echo "已撤销注入的历史回归，恢复放款导出资格过滤。"
else
  echo "没有检测到 inject_demo4_regression.sh 的注入标记，app/financing/service.py 已经是正确状态。"
fi

(cd "${workspace}" && ./verify.sh)
echo "如果 demo4_serve.sh 正在用 --reload 运行，改动会自动重启；如未生效，回到那个终端 Ctrl+C 后重新执行 ./scripts/demo4_serve.sh"

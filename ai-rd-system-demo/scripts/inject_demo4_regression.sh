#!/usr/bin/env bash
# 课堂脚本：确定性地把 D3 那次历史 bug 重新引入放款处理导出——
# 导出重新直接使用当前查询结果（rows），不再过滤放款导出资格，于是 REJECTED 又会被导出。
# 不依赖模型"碰巧"犯错；只用来证明沉淀下来的 ./verify.sh / Golden Case 能不能自己拦住这次回归。
#
# 用法：./scripts/inject_demo4_regression.sh
# 期望：workspaces/demo4-sedimentation 已经是"资产沉淀已完成"的状态
#      （通过 D4-2 live 沉淀，或 ./scripts/restore_demo4_sedimented.sh）。
set -euo pipefail
repo_root="$(cd "$(dirname "${0}")/.." && pwd)"
service_file="${repo_root}/workspaces/demo4-sedimentation/app/financing/service.py"

if [ ! -f "${service_file}" ]; then
  echo "找不到 ${service_file}，先运行 ./scripts/reset_demo4.sh 或 ./scripts/restore_demo4_sedimented.sh" >&2
  exit 1
fi

if grep -q "DEMO4-INJECTED-REGRESSION" "${service_file}"; then
  echo "回归已经注入过了（app/financing/service.py 已包含 DEMO4-INJECTED-REGRESSION 标记），无需重复注入"
  exit 0
fi

marker="for row in eligible_rows]"
if ! grep -qF "${marker}" "${service_file}"; then
  echo "没有在 ${service_file} 找到预期代码行（${marker}），无法确定性注入回归；" >&2
  echo "请检查文件是否已被改成其他写法，或先用 ./scripts/restore_demo4_sedimented.sh 恢复到已知状态。" >&2
  exit 1
fi

python3 - "${service_file}" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
text = text.replace(
    "for row in eligible_rows]",
    "for row in rows]  # DEMO4-INJECTED-REGRESSION",
    1,
)
open(path, "w", encoding="utf-8").write(text)
PY

echo "已注入历史回归：放款处理导出重新直接使用当前查询结果（未过滤放款导出资格）。"
echo "浏览器验证：状态筛选 REJECTED 时，查询和导出会同时显示 1 条。"
echo "确定性验证：(cd workspaces/demo4-sedimentation && ./verify.sh) 应该以 OVERALL: BLOCKED 结束。"

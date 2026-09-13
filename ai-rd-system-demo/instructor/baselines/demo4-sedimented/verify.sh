#!/usr/bin/env bash
# 项目标准验证入口：开发测试 + 放款处理导出资格 Golden Case（独立 policy gate）
# 都从这里进入。新 Agent 不需要知道 D3 那次事故的细节，只需要知道——改完必须跑这个。
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [ -x "../../.venv/bin/python" ]; then
  PYTHON="../../.venv/bin/python"
else
  PYTHON="python3"
fi

echo "== pytest（开发侧测试）=="
"${PYTHON}" -m pytest -q
pytest_status=$?

echo
echo "== golden/check_export_eligibility.py（独立 Golden Case / policy gate）=="
"${PYTHON}" golden/check_export_eligibility.py
golden_status=$?

echo
if [ "${pytest_status}" -eq 0 ] && [ "${golden_status}" -eq 0 ]; then
  echo "OVERALL: PASS"
  exit 0
fi
echo "OVERALL: BLOCKED"
exit 1

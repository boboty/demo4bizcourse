#!/usr/bin/env bash
# 开发侧验证：目前只跑 pytest。这个项目还没有独立于开发测试之外的 Golden Case /
# policy gate，也没有把放款处理导出资格规则沉淀成项目资产——那是本次任务要做的事。
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [ -x "../../.venv/bin/python" ]; then
  PYTHON="../../.venv/bin/python"
else
  PYTHON="python3"
fi
"${PYTHON}" -m pytest -q

#!/usr/bin/env bash
# 健康检查：确认当前工程是否还能工作。
# 这是开发侧自检，不是独立验收，不包含 Golden Case 或外部 Source of Truth。
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [ -x "../../.venv/bin/python" ]; then
  PYTHON="../../.venv/bin/python"
else
  PYTHON="python3"
fi
"$PYTHON" -m pytest -q

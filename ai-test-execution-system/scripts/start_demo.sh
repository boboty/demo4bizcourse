#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"

# 启动前环境变量是可选的确定性配置入口；未设置则保留现有状态。
if [[ -n "${UI_VERSION:-}${PAYMENT_MODE:-}${PRODUCT_BUG_MODE:-}" ]]; then
  UI_VERSION="${UI_VERSION:-v1}" PAYMENT_MODE="${PAYMENT_MODE:-normal}" PRODUCT_BUG_MODE="${PRODUCT_BUG_MODE:-off}" python3 - <<'PY'
import os
from app.runtime import RuntimeStore
RuntimeStore().reset(
    ui_version=os.environ["UI_VERSION"],
    payment_mode=os.environ["PAYMENT_MODE"],
    product_bug_mode=os.environ["PRODUCT_BUG_MODE"],
)
PY
fi

exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
